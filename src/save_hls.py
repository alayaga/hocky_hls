import argparse
from glob import glob
from pathlib import Path
import os
import subprocess
import time

def _fresh_check(m3u8_files):
    for m3u8 in m3u8_files:
        m3u8_mtime = os.path.getmtime(m3u8)
        if time.time() - m3u8_mtime > 10:
            print(f"Warning: {m3u8} has not been updated for more than 10 seconds.")
            return False
    return True

def record(src, dst, output_format="ts", is_vod=False):
    os.makedirs(dst, exist_ok=True)

    commands = []
    
    # Use glob pattern directly
    all_m3u8 = glob(src, recursive=True)
    
    if not all_m3u8:
        raise RuntimeError(f"No files found matching pattern: {src}")
    
    # Only check freshness when recording live streams (not VOD)
    if not is_vod and not _fresh_check(all_m3u8):
        raise RuntimeError("Some m3u8 files are stale. Aborting.")

    for m3u8 in all_m3u8:
        if output_format == "ts":
            dst_path = os.path.join(dst, f"{Path(m3u8).stem}.ts")
            commands.append(
                [
                    "ffmpeg",
                    "-y",
                    "-nostdin",
                    "-hide_banner",
                    "-copyts",
                    "-avoid_negative_ts", "disabled",
                    "-i", m3u8,
                    "-c", "copy",
                    "-map", "0",
                    "-copy_unknown",
                    '-muxdelay', '0',
                    '-muxpreload', '0',
                    dst_path,
                ]
            )
        elif output_format == "hls":
            stream_name = Path(m3u8).stem
            dst_path = os.path.join(dst, f"{stream_name}.m3u8")
            segment_pattern = os.path.join(dst, f"{stream_name}_%03d.ts")
            
            commands.append(
                [
                    "ffmpeg",
                    "-y",
                    "-nostdin",
                    "-hide_banner",
                    "-copyts",
                    "-avoid_negative_ts", "disabled",
                    "-i", m3u8,
                    "-c", "copy",
                    "-map", "0",
                    "-copy_unknown",
                    '-muxdelay', '0',
                    '-muxpreload', '0',
                    '-tag:v', 'hvc1',
                    "-f", "hls",
                    "-hls_time", "6",
                    "-hls_list_size", "0",
                    # use event for stream processing
                    # when process is killed, the end tag will be automatically added
                    "-hls_playlist_type", "event",
                    "-hls_segment_filename",
                    segment_pattern,
                    dst_path,
                ]
            )
    commands.sort()

    procs = []
    try:
        for idx, command in enumerate(commands):
            p = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=None if idx == 0 else subprocess.DEVNULL,
                stderr=None if idx == 0 else subprocess.DEVNULL,
            )
            procs.append(p)
        while True:
            exit_codes = set(p.poll() for p in procs)
            if exit_codes == {0}:
                print("All FFmpeg processes finished successfully.")
                break
            for code in exit_codes:
                if code is not None and code != 0:
                    raise RuntimeError(f"Error: FFmpeg process exited with code {code}. Exiting all.")
            time.sleep(1)
    except (KeyboardInterrupt, RuntimeError):
        print("Ctrl+C pressed, finishing recording...")
        for p in procs:
            p.stdin.write(b'q')
            p.stdin.flush()
        flag_kill = False
        t_end = time.perf_counter() + 300
        for p in procs:
            try:
                remain_timeout = max(0, t_end - time.perf_counter())
                p.wait(remain_timeout)
            except subprocess.TimeoutExpired:
                print(f"Error: FFmpeg process {p.pid} no response, terminating...")
                flag_kill = True
                p.kill()
        if not flag_kill:
            print("All record processes finished normally.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert HLS streams to TS files or static HLS VOD")
    parser.add_argument(
        "--src",
        "-s",
        type=str,
        required=True,
        help="Glob pattern for source files (e.g., '/path/**/*.m3u8' or '/path/stream_*')",
    )
    parser.add_argument(
        "--dst",
        "-d",
        type=str,
        required=True,
        help="Destination directory for output files",
    )
    parser.add_argument(
        "--format",
        "-f",
        type=str,
        default="ts",
        choices=["ts", "hls"],
        help="Output format: 'ts' for single TS file (default), 'hls' for static HLS VOD with 6s segments",
    )
    parser.add_argument(
        "--vod",
        "-v",
        default=False,
        action="store_true",
        help="VOD mode: convert existing files without checking freshness",
    )
    args = parser.parse_args()

    record(args.src, args.dst, args.format, args.vod)