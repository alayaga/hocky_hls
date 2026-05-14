SRC=/data/hls_live/*.m3u8
DST=/mnt/huawei-storage/record/$(date +%Y%m%d_%H%M%S)/
mkdir -p $DST
python3 save_hls.py -s "$SRC" -d "$DST" -f hls -v