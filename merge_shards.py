import os

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
    shards = ['a', 'b', 'c', 'd', 'e']
    status = {s: is_shard_done(s) for s in shards}

    print(f"🔍 分片状态：")
    for s in shards:
        print(f"   分片 {s.upper()}：{'✅ 完成' if status[s] else '⏳ 进行中'}")

    # 必须全部分片都完成才合并
    if not all(status.values()):
        print("⏳ 分片尚未全部完成，跳过合并。")
        return

    print("✅ 全部分片均已完成，开始合并...")

    merged_list = []
    for s in shards:
        lines = read_lines(f'valid_links_{s}.txt')
        print(f"📊 分片 {s.upper()} 有效：{len(lines)} 条")
        merged_list.extend(lines)

    existing = read_lines('valid_links.txt')
    print(f"📊 历史有效：{len(existing)} 条")

    # 去重但保持插入顺序（历史在前，新增追加到末尾）
    merged = list(dict.fromkeys(existing + merged_list))
    write_lines('valid_links.txt', merged)

    print(f"✅ 合并后总数：{len(merged)} 条（去重保序）")

if __name__ == '__main__':
    main()
