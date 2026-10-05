import requests
import time
import os
import sys
import argparse
import re
from datetime import date, timedelta

BASE_URL = "http://bfts.5read.com/pdz/"
SUFFIX = "unRegister.pdz"
SS_LIST_FILE = "ss_list.txt"
TIMEOUT = 30
REQUEST_DELAY = 0.25
SHARD_A_END = 40000            # 分片 A 处理 0–39999

# 全局：由 --shard 参数决定
SHARD = ""
PROGRESS_FILE = "progress.txt"
VALID_OUTPUT_FILE = "valid_links.txt"
ROUND_DATE_FILE = "round_done.txt"

def configure_files(shard):
    """根据分片标识设置文件名"""
    global SHARD, PROGRESS_FILE, VALID_OUTPUT_FILE, ROUND_DATE_FILE
    SHARD = shard
    if shard in ("a", "b"):
        PROGRESS_FILE   = f"progress_{shard}.txt"
        VALID_OUTPUT_FILE = f"valid_links_{shard}.txt"
        ROUND_DATE_FILE = f"round_done_{shard}.txt"
    else:
        PROGRESS_FILE   = "progress.txt"
        VALID_OUTPUT_FILE = "valid_links.txt"
        ROUND_DATE_FILE = "round_done.txt"

def load_ss_list():
    if not os.path.exists(SS_LIST_FILE):
        print(f"❌ 错误：找不到 {SS_LIST_FILE}")
        sys.exit(1)
    with open(SS_LIST_FILE, "r", encoding="utf-8") as f:
        full = [line.strip() for line in f if line.strip().isdigit()]
    if SHARD == "a":
        return full[:SHARD_A_END]
    elif SHARD == "b":
        return full[SHARD_A_END:]
    return full

def load_valid_set():
    """
    读取有效链接集合：
    - 历史存档 valid_links.txt
    - 本分片自己的 valid_links_a.txt / valid_links_b.txt
    """
    valid_set = set()
    files_to_read = ["valid_links.txt"]
    if SHARD in ("a", "b"):
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

def get_round_done_date():
    if os.path.exists(ROUND_DATE_FILE):
        with open(ROUND_DATE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None

def set_round_done_date(d):
    with open(ROUND_DATE_FILE, "w", encoding="utf-8") as f:
        f.write(d)

def append_valid_link(url):
    with open(VALID_OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")

def cleanup_old_snapshots(keep_days=10):
    """清理超过保留天数的快照文件"""
    cutoff = date.today() - timedelta(days=keep_days)
    cutoff_str = cutoff.isoformat()
    for f in os.listdir("."):
        if f.startswith("valid_") and f.endswith(".txt") and f != VALID_OUTPUT_FILE and not f.startswith("valid_links"):
            match = re.search(r'(\d{4}-\d{2}-\d{2})', f)
            if match:
                date_part = match.group(1)
                if date_part < cutoff_str:
                    try:
                        os.remove(f)
                        print(f"🗑️ 删除旧快照: {f}")
                    except Exception as e:
                        print(f"⚠️ 删除 {f} 失败: {e}")

def create_snapshot():
    if not os.path.exists(VALID_OUTPUT_FILE):
        return
    today = date.today().isoformat()
    prefix = f"valid_{SHARD}_" if SHARD else "valid_"
    snapshot_name = f"{prefix}{today}.txt"
    try:
        with open(VALID_OUTPUT_FILE, "r", encoding="utf-8") as src:
            content = src.read()
        with open(snapshot_name, "w", encoding="utf-8") as dst:
            dst.write(content)
        print(f"📸 已生成快照：{snapshot_name}")
    except Exception as e:
        print(f"⚠️ 生成快照失败：{e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-minutes', type=int, default=350)
    parser.add_argument('--shard', type=str, default='',
                        help='分片标识：a / b，留空为单线程模式')
    args = parser.parse_args()
    configure_files(args.shard)
    max_run_seconds = args.max_minutes * 60

    ss_list = load_ss_list()
    total = len(ss_list)
    print(f"📊 [分片 {SHARD or '单线程'}] 总SS数：{total}")

    valid_set = load_valid_set()
    print(f"✅ 当前有效SS数（含历史）：{len(valid_set)}")

    if len(valid_set) == total:
        print("🎉 本分片所有SS已有效，任务完成。")
        for f in [PROGRESS_FILE, ROUND_DATE_FILE]:
            if os.path.exists(f):
                os.remove(f)
        cleanup_old_snapshots()
        create_snapshot()
        return

    cur = get_progress()
    today = date.today().isoformat()

    # ★★★ 关键改动：分片完成后不再自动重置，直接退出等待另一个分片 ★★★
    if cur == -1:
        print(f"⏸️ 分片 {SHARD} 已完成，等待另一个分片...")
        return

    if cur >= total:
        cur = 0
        set_progress(cur)

    print(f"⏳ 从索引 {cur} 开始")

    start_time = time.time()
    while cur < total:
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
    set_round_done_date(today)
    set_progress(-1)
    create_snapshot()
    cleanup_old_snapshots()

if __name__ == "__main__":
    main()
