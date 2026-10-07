import requests
import time
import os
import sys
import argparse
import re
from datetime import date, timedelta, datetime, timezone

BASE_URL = "http://bfts.5read.com/pdz/"
SUFFIX = "unRegister.pdz"
SS_LIST_FILE = "ss_list.txt"
TIMEOUT = 30
REQUEST_DELAY = 0.25
SHARD_A_END = 10441
SHARD_B_END = 20882
SHARD_C_END = 31323
SHARD_D_END = 41764
SHARD_E_END = 52205
SHARD_F_END = 62646
SHARD_G_END = 73087
SNAPSHOT_DIR = "snapshots"

# 北京时区 + 停止线
BJ_TZ = timezone(timedelta(hours=8))
STOP_HOUR = 23
STOP_MINUTE = 50

# 全局：由 --shard 参数决定
SHARD = ""
PROGRESS_FILE = "progress.txt"
VALID_OUTPUT_FILE = "valid_links.txt"

def is_past_stop_time():
    """是否到达北京 23:50 停止线"""
    now = datetime.now(BJ_TZ)
    return (now.hour > STOP_HOUR) or (now.hour == STOP_HOUR and now.minute >= STOP_MINUTE)

def configure_files(shard):
    global SHARD, PROGRESS_FILE, VALID_OUTPUT_FILE
    SHARD = shard
    if shard in ("a", "b", "c", "d", "e", "f", "g", "h"):
        PROGRESS_FILE   = f"progress_{shard}.txt"
        VALID_OUTPUT_FILE = f"valid_links_{shard}.txt"
    else:
        PROGRESS_FILE   = "progress.txt"
        VALID_OUTPUT_FILE = "valid_links.txt"

def load_ss_list():
    if not os.path.exists(SS_LIST_FILE):
        print(f"❌ 错误：找不到 {SS_LIST_FILE}")
        sys.exit(1)
    with open(SS_LIST_FILE, "r", encoding="utf-8") as f:
        full = [line.strip() for line in f if line.strip().isdigit()]
    if SHARD == "a":
        return full[:SHARD_A_END]
    elif SHARD == "b":
        return full[SHARD_A_END:SHARD_B_END]
    elif SHARD == "c":
        return full[SHARD_B_END:SHARD_C_END]
    elif SHARD == "d":
        return full[SHARD_C_END:SHARD_D_END]
    elif SHARD == "e":
        return full[SHARD_D_END:SHARD_E_END]
    elif SHARD == "f":
        return full[SHARD_E_END:SHARD_F_END]
    elif SHARD == "g":
        return full[SHARD_F_END:SHARD_G_END]
    elif SHARD == "h":
        return full[SHARD_G_END:]
    return full

def load_valid_set():
    valid_set = set()
    files_to_read = ["valid_links.txt"]
    if SHARD in ("a", "b", "c", "d", "e", "f", "g", "h"):
        files_to_read.append(VALID_OUTPUT_FILE)

    for path in files_to_read:
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                url = line.strip()
                if not url:
                    continue
                if "/pdz/" in url and "unRegister.pdz" in url:
                    try:
                        ss = url.split("/pdz/")[1].replace("unRegister.pdz", "")
                        valid_set.add(ss)
                    except:
                        pass
    return valid_set

def get_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            val = f.read().strip()
            if val == "-1":
                return -1
            if val.isdigit():
                return int(val)
    return 0

def set_progress(idx):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        f.write(str(idx))

def append_valid_link(url):
    with open(VALID_OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")

def cleanup_old_snapshots(keep_days=10):
    if not os.path.isdir(SNAPSHOT_DIR):
        return
    cutoff_str = (date.today() - timedelta(days=keep_days)).isoformat()
    for f in os.listdir(SNAPSHOT_DIR):
        if not (f.startswith("valid_") and f.endswith(".txt")):
            continue
        match = re.search(r'(\d{4}-\d{2}-\d{2})', f)
        if match and match.group(1) < cutoff_str:
            path = os.path.join(SNAPSHOT_DIR, f)
            try:
                os.remove(path)
                print(f"🗑️ 删除旧快照: {f}")
            except Exception as e:
                print(f"⚠️ 删除 {f} 失败: {e}")

def create_snapshot():
    if not os.path.exists(VALID_OUTPUT_FILE):
        return
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    today = date.today().isoformat()
    prefix = f"valid_{SHARD}_" if SHARD else "valid_"
    snapshot_name = f"{prefix}{today}.txt"
    snapshot_path = os.path.join(SNAPSHOT_DIR, snapshot_name)
    try:
        with open(VALID_OUTPUT_FILE, "r", encoding="utf-8") as src:
            content = src.read()
        with open(snapshot_path, "w", encoding="utf-8") as dst:
            dst.write(content)
        print(f"📸 已生成快照：{SNAPSHOT_DIR}/{snapshot_name}")
    except Exception as e:
        print(f"⚠️ 生成快照失败：{e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-minutes', type=int, default=350)
    parser.add_argument('--shard', type=str, default='')
    args = parser.parse_args()
    configure_files(args.shard)
    max_run_seconds = args.max_minutes * 60

    ss_list = load_ss_list()
    total = len(ss_list)
    print(f"📊 [分片 {SHARD or '单线程'}] 总SS数：{total}")

    valid_set = load_valid_set()
    print(f"✅ 当前有效SS数（含历史）：{len(valid_set)}")

    if all(ss in valid_set for ss in ss_list):
        print("🎉 本分片所有SS已有效，任务完成。")
        set_progress(-1)
        cleanup_old_snapshots()
        create_snapshot()
        return

    cur = get_progress()

    if cur == -1:
        print(f"⏸️ 分片 {SHARD} 已完成，等待其他分片...")
        return

    if cur >= total:
        cur = 0
        set_progress(cur)

    print(f"⏳ 从索引 {cur} 开始")

    start_time = time.time()
    while cur < total:
        # ★ 23:50 停止线检查
        if is_past_stop_time():
            print(f"\n🛑 北京时间 {datetime.now(BJ_TZ).strftime('%H:%M')}，达到 23:50 停止线")
            print(f"   已扫到 {cur}/{total}，标记为可合并退出")
            set_progress(-1)
            create_snapshot()
            cleanup_old_snapshots()
            return

        elapsed = time.time() - start_time
        if elapsed > max_run_seconds:
            set_progress(cur)
            print(f"⏰ 时间到，保存进度 {cur}，退出。")
            return

        ss = ss_list[cur]
        if ss in valid_set:
            cur += 1
            set_progress(cur)
            continue

        url = f"{BASE_URL}{ss}{SUFFIX}"
        print(f"[{SHARD or 'S'}:{cur+1}/{total}] 检测 {ss} ... ", end="")
        try:
            r = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
            if r.status_code == 200:
                print("✅ 有效")
                valid_set.add(ss)
                append_valid_link(url)
            else:
                print(f"❌ 无效 ({r.status_code})")
        except Exception as e:
            print(f"⚠️ 异常: {str(e)[:30]}")

        cur += 1
        set_progress(cur)
        time.sleep(REQUEST_DELAY)

    print("✅ 本轮检测完成！")
    set_progress(-1)
    create_snapshot()
    cleanup_old_snapshots()

if __name__ == "__main__":
    main()
