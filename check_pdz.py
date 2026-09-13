import requests
import time
import argparse
import sys
import os
import datetime

# ======================== 配置参数 ========================
SS_LIST_FILE = 'ss_list.txt'
PROGRESS_FILE = 'progress.txt'
VALID_LINKS_FILE = 'valid_links.txt'
ROUND_DONE_FILE = 'round_done.txt'

TIMEOUT = 30
REQUEST_DELAY = 0.3
COOLDOWN_HOURS = 48  # 每轮完成后冷却 48 小时
# =========================================================


def load_ss_list():
    with open(SS_LIST_FILE, 'r') as f:
        return [line.strip() for line in f if line.strip()]


def load_valid_links():
    if not os.path.exists(VALID_LINKS_FILE):
        return set()
    with open(VALID_LINKS_FILE, 'r') as f:
        return set(line.strip() for line in f if line.strip())


def load_progress():
    """读取进度，-1 表示上一轮已完成"""
    if not os.path.exists(PROGRESS_FILE):
        return 0
    with open(PROGRESS_FILE, 'r') as f:
        content = f.read().strip()
    try:
        return int(content)
    except:
        return 0


def save_progress(index):
    with open(PROGRESS_FILE, 'w') as f:
        f.write(str(index))


def save_valid_link(ss):
    with open(VALID_LINKS_FILE, 'a') as f:
        f.write(ss + '\n')


# ======================== 48小时冷却机制 ========================
def get_round_done_time():
    """读取上一轮完成的时间戳；无记录返回 None"""
    if not os.path.exists(ROUND_DONE_FILE):
        return None
    with open(ROUND_DONE_FILE, 'r') as f:
        content = f.read().strip()
    if not content:
        return None
    try:
        return datetime.datetime.strptime(content, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return None


def is_in_cooldown():
    """判断是否还在 48 小时冷却期内"""
    last_done = get_round_done_time()
    if last_done is None:
        return False
    elapsed = datetime.datetime.now() - last_done
    return elapsed < datetime.timedelta(hours=COOLDOWN_HOURS)


def mark_round_done():
    """记录轮次完成时刻"""
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(ROUND_DONE_FILE, 'w') as f:
        f.write(now)
    print(f"📌 本轮完成，冷却期开始（{COOLDOWN_HOURS} 小时后可开启下一轮）")


def clear_round_done():
    """清空轮次完成标记，准备开始新一轮"""
    with open(ROUND_DONE_FILE, 'w') as f:
        f.write('')
# =========================================================


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-minutes', type=int, default=0, help='最大运行分钟数')
    args = parser.parse_args()
    max_minutes = args.max_minutes

    # ---------- 冷却期检查 ----------
    progress = load_progress()

    if progress == -1:
        # 上一轮已完成，检查冷却期
        if is_in_cooldown():
            last_done = get_round_done_time()
            elapsed = datetime.datetime.now() - last_done
            remaining = datetime.timedelta(hours=COOLDOWN_HOURS) - elapsed
            print(f"⏸️ 轮次冷却中 | 距上次完成 {elapsed} | 还需等待约 {remaining}")
            sys.exit(0)
        else:
            # 冷却结束，开始新一轮
            last_done = get_round_done_time()
            if last_done:
                elapsed = datetime.datetime.now() - last_done
                print(f"🔄 冷却期已过（距上次完成 {elapsed}），开始新一轮检测")
            else:
                print("🔄 开始新一轮检测")
            clear_round_done()
            save_progress(0)
            progress = 0

    # ---------- 加载数据 ----------
    ss_list = load_ss_list()
    valid_set = load_valid_links()
    start_index = progress
    total = len(ss_list)

    if start_index >= total:
        print("🎉 本轮全部检测完毕，标记完成。")
        mark_round_done()
        save_progress(-1)
        sys.exit(0)

    print(f"🚀 开始检测 | 总数: {total} | 起始: {start_index} | 已有效: {len(valid_set)}")
    start_time = time.time()

    for idx in range(start_index, total):
        ss = ss_list[idx]

        # 跳过已有效的
        if ss in valid_set:
            print(f"[{idx+1}/{total}] {ss} 已有效，跳过。")
            save_progress(idx + 1)
            continue

        # 检查运行时长
        elapsed_minutes = (time.time() - start_time) / 60
        if max_minutes > 0 and elapsed_minutes > max_minutes:
            print(f"⏰ 达到最大运行时间 ({max_minutes} 分钟)，保存进度并退出。")
            save_progress(idx)
            sys.exit(0)

        url = f"http://bfts.5read.com/pdz/{ss}unRegister.pdz"

        try:
            resp = requests.head(url, timeout=TIMEOUT, allow_redirects=False)
            if resp.status_code == 200:
                print(f"[{idx+1}/{total}] ✅ {ss} 有效 (Status: 200)")
                valid_set.add(ss)
                save_valid_link(ss)
            else:
                print(f"[{idx+1}/{total}] ❌ {ss} 无效 (Status: {resp.status_code})")

        except requests.exceptions.ConnectionError as e:
            print(f"[{idx+1}/{total}] ⚠️ 网络连接错误: {e}")
            save_progress(idx)
            sys.exit(1)
        except Exception as e:
            print(f"[{idx+1}/{total}] ⚠️ 未知错误: {e}")
            save_progress(idx)
            sys.exit(1)

        save_progress(idx + 1)
        time.sleep(REQUEST_DELAY)

    # ---------- 全部完成 ----------
    print("🎉 所有 SS 号检测完成！")
    mark_round_done()
    save_progress(-1)


if __name__ == "__main__":
    main()
