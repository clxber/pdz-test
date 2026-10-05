import os
import datetime

def read_lines(path):
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def write_lines(path, lines):
    with open(path, 'w', encoding='utf-8') as f:
        for line in lines:
            f.write(line + '\n')

def is_shard_done(shard):
    prog = f'progress_{shard}.txt'
    if not os.path.exists(prog):
        return False
    with open(prog, 'r', encoding='utf-8') as f:
        return f.read().strip() == '-1'

def main():
    a_done = is_shard_done('a')
    b_done = is_shard_done('b')

    print(f"🔍 分片状态：")
    print(f"   分片 A：{'✅ 完成' if a_done else '⏳ 进行中'}")
    print(f"   分片 B：{'✅ 完成' if b_done else '⏳ 进行中'}")

    # ★★★ 关键改动：必须两个分片都完成才合并 ★★★
    if not (a_done and b_done):
        print("⏳ 两个分片尚未全部完成，跳过合并。")
        return

    print("✅ 两个分片均已完成，开始合并...")

    a = read_lines('valid_links_a.txt')
    b = read_lines('valid_links_b.txt')
    existing = read_lines('valid_links.txt')

    merged = sorted(set(existing + a + b))
    write_lines('valid_links.txt', merged)

    print(f"📊 分片 A 有效：{len(a)} 条")
    print(f"📊 分片 B 有效：{len(b)} 条")
    print(f"📊 历史有效：{len(existing)} 条")
    print(f"✅ 合并后总数：{len(merged)} 条（自动去重）")

    today = datetime.date.today().isoformat()
    with open('round_done.txt', 'w', encoding='utf-8') as f:
        f.write(today)
    print(f"📌 整轮完成，写入 round_done.txt = {today}")

if __name__ == '__main__':
    main()
