import os
import subprocess
import time
import logging
import shutil

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SAVE_HLS_SCRIPT = os.path.join(os.path.dirname(__file__), "save_hls.py")


class RecordManager:
    def __init__(self):
        self.active_tasks = {}
        self.disk_critical = False

    def start_recording(self, match_id: str, segment_id: str, src_pattern: str, base_dst: str):
        if self.disk_critical:
            return False, "磁盘空间不足，拒绝录制"

        task_key = f"match_{match_id}_seg_{segment_id}"
        if task_key in self.active_tasks:
            return False, "该任务已在录制中"

        target_dir = os.path.join(base_dst, f"match_{match_id}", f"segment{segment_id}")
        os.makedirs(target_dir, exist_ok=True)

        src_glob = src_pattern
        if os.path.isdir(src_pattern):
            src_glob = os.path.join(src_pattern, "*.m3u8")
            logging.info(f"目录模式匹配: {src_glob}")

        from glob import glob
        all_m3u8 = [f for f in glob(src_glob) if os.path.isfile(f)]
        if not all_m3u8:
            return False, f"未发现匹配的流文件: {src_glob}"

        cmd = [
            "python", SAVE_HLS_SCRIPT,
            "-s", src_glob,
            "-d", target_dir,
            "-f", "hls",
            "-v"
        ]
        logging.info(f"启动 save_hls.py: {' '.join(cmd)}")

        try:
            p = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )
            self.active_tasks[task_key] = p
            logging.info(f"save_hls.py 启动成功 (PID: {p.pid})")
            return True, target_dir
        except Exception as e:
            logging.error(f"启动异常: {str(e)}")
            return False, str(e)

    def stop_recording(self, match_id: str, segment_id: str):
        task_key = f"match_{match_id}_seg_{segment_id}"
        if task_key not in self.active_tasks:
            return False, "未找到任务"

        p = self.active_tasks.pop(task_key)
        try:
            p.stdin.write(b'q')
            p.stdin.flush()
            logging.info(f"已发送停止信号到 {task_key}，等待优雅退出...")
            p.wait(timeout=300)
            logging.info(f"{task_key} 已正常退出")
        except subprocess.TimeoutExpired:
            logging.warning(f"{task_key} 超时未退出，强制终止")
            p.kill()
        except Exception as e:
            logging.error(f"停止异常: {e}")
            p.kill()

        return True, "已停止录制"

    def stop_all_recordings(self):
        if not self.active_tasks:
            return True, "无活跃任务"
        task_keys = list(self.active_tasks.keys())
        count = len(task_keys)
        for task_key in task_keys:
            parts = task_key.split("_")
            if len(parts) >= 4:
                self.stop_recording(parts[1], parts[3])
        logging.info(f"已批量停止 {count} 个任务")
        return True, f"已停止 {count} 个任务"

    def check_disk_space(self, path, threshold):
        try:
            total, used, free = shutil.disk_usage(path)
            free = free / (1024 * 1024 * 1024)
            if free < threshold:
                logging.warning(f"[DISK] 磁盘空间不足: {free:.2f}GB < {threshold}GB")
                self.disk_critical = True
                return True, free
            self.disk_critical = False
            return False, free
        except Exception as e:
            logging.error(f"检查磁盘空间异常: {str(e)}")
            self.disk_critical = True
            return True, 0
