from fastapi import FastAPI,BackgroundTasks,WebSocket,WebSocketDisconnect
from record import RecordManager
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("hocky_hls")

# SRC_PATH = "/data/hls_live"
# DST_PATH = "/app/data"
SRC_PATH = r"F:\TheHockeyProject\test\data\hls_live"
DST_PATH = r"F:\TheHockeyProject\test\hockey_video"

recorder = RecordManager()

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"[WS] 客户端已连接，当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"[WS] 客户端已断开，当前连接数: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        logger.info(f"[WS] 准备广播消息: {message}, 当前连接数: {len(self.active_connections)}")
        if not self.active_connections:
            logger.warning("[WS] 没有活跃的 WebSocket 连接，广播跳过")
            return
        for i, connection in enumerate(self.active_connections):
            try:
                await connection.send_json(message)
                logger.info(f"[WS] 广播成功: 连接 #{i}")
            except Exception as e:
                logger.error(f"[WS] 广播失败: 连接 #{i}, 错误: {e}")

manager = ConnectionManager()
async def monitor_disk():
    logger.info("[DISK] 磁盘监控任务已启动，阈值: 80GB，检查间隔: 5秒")
    alert = False
    while True:
        stopped, free_space = recorder.check_disk_space(DST_PATH, 80)
        logger.info(f"[DISK] 剩余: {free_space:.2f}GB | WS连接数: {len(manager.active_connections)} | 录制任务数: {len(recorder.active_tasks)}")
        if stopped:
            if not alert:
                logger.warning(f"[DISK] 磁盘空间不足! 剩余: {free_space:.2f}GB，准备广播 DISK_CRITICAL")
                await manager.broadcast({
                    "type": "DISK_CRITICAL",
                    "message": f"磁盘空间不足({free_space:.2f}GB)，已停止所有录制",
                    "free_space": free_space
                })
                alert = True
                logger.info("[DISK] 异步执行 stop_all_recordings")
                asyncio.get_event_loop().run_in_executor(None, recorder.stop_all_recordings)
            else:
                logger.info(f"[DISK] 磁盘仍不足({free_space:.2f}GB)，alert 已激活，不重复广播")
        else:
            if alert:
                logger.info(f"[DISK] 磁盘空间已恢复: {free_space:.2f}GB，准备广播 DISK_OK")
                await manager.broadcast({
                    "type": "DISK_OK",
                    "message": f"磁盘空间已恢复({free_space:.2f}GB)",
                    "free_space": free_space
                })
                alert = False
        await asyncio.sleep(5)
@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(monitor_disk())
    logger.info("[APP] 录制后端已启动，磁盘监控任务已创建")
    yield
    task.cancel()
    logger.info("[APP] 录制后端关闭")

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    logger.info("[WS] 收到 WebSocket 连接请求")
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"[WS] 收到客户端消息: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"[WS] 连接异常: {e}")
        manager.disconnect(websocket)
@app.post("/api/hls_start")
async def start_hls(match_id:int,segment_id:int):
    logger.info(f"[API] 收到 hls_start 请求: match_id={match_id}, segment_id={segment_id}")
    try:
        success,result = recorder.start_recording(match_id,segment_id,SRC_PATH,DST_PATH)
        if success:
            logger.info(f"[API] hls_start 成功: {result}")
            return f"success start, save to {result}"
        logger.warning(f"[API] hls_start 失败: {result}")
        return {"error": result}
    except Exception as e:
        logger.error(f"[API] hls_start 异常: {e}")
        return {"error": str(e)}

@app.post("/api/hls_stop")
async def stop_hls(background_tasks: BackgroundTasks):
    logger.info("[API] 收到 hls_stop 请求")
    try:
        background_tasks.add_task(recorder.stop_all_recordings)
        return {"status": "stopping_in_background"}
    except Exception as e:
        logger.error(f"[API] hls_stop 异常: {e}")
        return "error"

@app.post("/api/test_alert")
async def test_alert():
    logger.info(f"[TEST] 手动触发 DISK_CRITICAL 测试，当前连接数: {len(manager.active_connections)}")
    await manager.broadcast({
        "type": "DISK_CRITICAL",
        "message": "测试告警：磁盘空间不足",
        "free_space": 0.0
    })
    return {"status": "alert_sent", "connections": len(manager.active_connections)}
