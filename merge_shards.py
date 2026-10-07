import os

def read_lines(path):
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def is_shard_done(shard):
    prog = f'progress_{shard}.txt'
    if not os.path.exists(prog):
        return False
    with open(prog, 'r', encoding='utf-8') as f:
        return f.read().strip() == '-1'

def main():
    shards = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    status = {s: is_shard_done(s) for s in shards}

    print(f"🔍 分片状态：")
    for s in shards:
        print(f"   分片 {s.upper()}：{'✅ 完成' if status[s] else '⏳ 进行中'}")

    # 必须全部分片都完成才合并
    if not all(status.values()):
        print("⏳ 分片尚未全部完成，跳过合并。")
        return

    print("✅ 全部分片均已完成，开始合并...")

    # 读总库（用于去重）
    existing = read_lines('valid_links.txt')
    existing_set = set(existing)
    print(f"📊 总库当前：{len(existing)} 条")

    # 收集各分片本轮新增
    new_lines = []
    for s in shards:
        lines = read_lines(f'valid_links_{s}.txt')
        print(f"📊 分片 {s.upper()} 本轮新增：{len(lines)} 条")
        for line in lines:
            if line not in existing_set:
                new_lines.append(line)
                existing_set.add(line)

    # ★ 物理追加写总库（不重写整个文件）
    if new_lines:
        with open('valid_links.txt', 'a', encoding='utf-8') as f:
            for line in new_lines:
                f.write(line + '\n')
        print(f"✅ 追加 {len(new_lines)} 条新有效链接到总库")
    else:
        print("ℹ️ 本轮无新增有效链接")

    print(f"✅ 总库当前总数：{len(existing) + len(new_lines)} 条")

    # ★ 清空所有分片文件（本轮缓冲用完即清）
    for s in shards:
        with open(f'valid_links_{s}.txt', 'w', encoding='utf-8') as f:
            f.write('')
    print(f"✅ 已清空 {len(shards)} 个分片文件")

if __name__ == '__main__':
    main()
