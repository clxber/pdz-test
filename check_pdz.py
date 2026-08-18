import requests
import time
import os
import sys
import argparse
from datetime import datetime, date, timedelta
import re

BASE_URL = "http://bfts.5read.com/pdz/"
SUFFIX = "unRegister.pdz"
SS_LIST_FILE = "ss_list.txt"
VALID_OUTPUT_FILE = "valid_links.txt"
PROGRESS_FILE = "progress.txt"
ROUND_DATE_FILE = "round_done.txt"
TIMEOUT = 30
REQUEST_DELAY = 0.3

def load_ss_list():
    if not os.path.exists(SS_LIST_FILE):
        print(f"❌ 错误：找不到 {SS_LIST_FILE}")
        sys.exit(1)
    with open(SS_LIST_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip().isdigit()]

def load_valid_set():
    valid_set = set()
    if os.path.exists(VALID_OUTPUT_FILE):
        with open(VALID_OUTPUT_FILE, "r", encoding="utf-8") as f:
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

def cleanup_old_snapshots(keep_days=30):
    cutoff = date.today() - timedelta(days=keep_days)
    cutoff_str = cutoff.isoformat()
    for f in os.listdir("."):
        if f.startswith("valid_") and f.endswith(".txt") and f != "valid_links.txt":
            try:
                date_part = f[6:16]
                if date_part < cutoff_str:
                    os.remove(f)
                    print(f"🗑️ 删除旧快照: {f}")
            except:
                pass

def create_snapshot():
    if not os.path.exists(VALID_OUTPUT_FILE):
        print("⚠️ 没有有效链接可生成快照")
        return
    today = date.today().isoformat()
    snapshot_name = f"valid_{today}.txt"
    try:
        with open(VALID_OUTPUT_FILE, "r", encoding="utf-8") as src:
            content = src.read()
        with open(snapshot_name, "w", encoding="utf-8") as dst:
            dst.write(content)
        print(f"📸 已生成快照：{snapshot_name}")
    except Exception as e:
        print(f"⚠️ 生成快照失败：{e}")

# 此函数已不再使用，保留但不会调用
def create_email_flag():
    today = date.today().isoformat()
    flag_file = f"email_notify_{today}.txt"
    with open(flag_file, "w", encoding="utf-8") as f:
        f.write("本轮检测完成，请查收附件。")
    print(f"📧 已创建邮件通知标志：{flag_file}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-minutes', type=int, default=44,
                        help='每次运行的最大分钟数')
    args = parser.parse_args()
    max_run_seconds = args.max_minutes * 60

    ss_list = load_ss_list()
    total = len(ss_list)
    print(f"📊 总SS数：{total}")

    valid_set = load_valid_set()
    print(f"✅ 当前有效SS数：{len(valid_set)}")

    if len(valid_set) == total:
        print("🎉 所有SS已有效，任务完成。")
        for f in [PROGRESS_FILE, ROUND_DATE_FILE]:
            if os.path.exists(f):
                os.remove(f)
        cleanup_old_snapshots()
        create_snapshot()
        # create_email_flag()   # ✅ 已注释掉，不再生成邮件标志文件
        return

    cur = get_progress()
    today = date.today().isoformat()
    done_date = get_round_done_date()

    if cur == -1:
        if done_date == today:
            print("⏳ 今日已完成一轮检测，退出。")
            return
        else:
            cur = 0
            set_progress(cur)
            set_round_done_date("")

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
        print(f"[{cur+1}/{total}] 检测 {ss} ... ", end="")
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
    # create_email_flag()   # ✅ 已注释掉，不再生成邮件标志文件
    cleanup_old_snapshots()

if __name__ == "__main__":
    main()
