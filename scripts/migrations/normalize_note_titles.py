#!/usr/bin/env python3
"""
笔记标题规范化迁移脚本

将笔记标题规范化为 【主题-币种-序号】 格式。

规范化规则：
- 【妖币研究 #92】TRADOOR 涨幅580%特征分析 -> 【妖币研究-TRADOOR-92】涨幅580%特征分析
- #50 BRETT 2024.08-12 涨跌特征研究 -> 【妖币研究-BRETT-50】2024.08-12涨跌特征研究
- [妖币研究 #60] XPIN 12天涨14倍特征分析 -> 【妖币研究-XPIN-60】12天涨14倍特征分析
- 【快速研究 #21】FLOKI 经典Meme币爆发分析 -> 【妖币研究-FLOKI-21】经典Meme币爆发分析

使用方法：
    python scripts/migrations/normalize_note_titles.py --dry-run  # 预览变更
    python scripts/migrations/normalize_note_titles.py            # 执行变更
"""

import re
import sys
import argparse
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from domains.note_hub.services.note_service import NoteService


def parse_title(title: str) -> dict | None:
    """
    解析笔记标题，提取主题、币种、序号和描述

    Returns:
        dict with keys: topic, coin, number, description
        None if title doesn't match any pattern
    """
    # 模式1: 【妖币研究 #92】TRADOOR 涨幅580%特征分析
    pattern1 = r'^【(妖币研究)\s*#(\d+)】\s*([A-Z0-9]+)\s+(.+)$'
    match = re.match(pattern1, title)
    if match:
        return {
            'topic': match.group(1),
            'coin': match.group(3),
            'number': match.group(2),
            'description': match.group(4),
        }

    # 模式2: 【快速研究 #21】FLOKI 经典Meme币爆发分析 (2024.02-03)
    pattern2 = r'^【快速研究\s*#(\d+)】\s*([A-Z0-9]+)\s+(.+)$'
    match = re.match(pattern2, title)
    if match:
        return {
            'topic': '妖币研究',
            'coin': match.group(2),
            'number': match.group(1),
            'description': match.group(3),
        }

    # 模式3: [妖币研究 #60] XPIN 12天涨14倍特征分析
    pattern3 = r'^\[妖币研究\s*#(\d+)\]\s*([A-Z0-9]+)\s+(.+)$'
    match = re.match(pattern3, title)
    if match:
        return {
            'topic': '妖币研究',
            'coin': match.group(2),
            'number': match.group(1),
            'description': match.group(3),
        }

    # 模式4: #50 BRETT 2024.08-12 涨跌特征研究
    pattern4 = r'^#(\d+)\s+([A-Z0-9]+)\s+(.+)$'
    match = re.match(pattern4, title)
    if match:
        return {
            'topic': '妖币研究',
            'coin': match.group(2),
            'number': match.group(1),
            'description': match.group(3),
        }

    return None


def normalize_title(parsed: dict) -> str:
    """生成规范化标题"""
    return f"【{parsed['topic']}-{parsed['coin']}-{parsed['number']}】{parsed['description']}"


def main():
    parser = argparse.ArgumentParser(description='规范化笔记标题')
    parser.add_argument('--dry-run', action='store_true', help='预览变更，不实际执行')
    args = parser.parse_args()

    service = NoteService()

    # 获取所有笔记
    all_notes = []
    page = 1
    page_size = 50

    while True:
        notes, total = service.list_notes(page=page, page_size=page_size, is_archived=None)
        all_notes.extend(notes)
        if len(all_notes) >= total:
            break
        page += 1

    print(f"共找到 {len(all_notes)} 条笔记\n")

    # 分析需要规范化的笔记
    updates = []
    for note in all_notes:
        parsed = parse_title(note.title)
        if parsed:
            new_title = normalize_title(parsed)
            if new_title != note.title:
                updates.append({
                    'id': note.id,
                    'old_title': note.title,
                    'new_title': new_title,
                })

    if not updates:
        print("没有需要规范化的笔记")
        return

    print(f"需要规范化 {len(updates)} 条笔记:\n")

    # 显示变更预览
    for i, update in enumerate(updates, 1):
        print(f"[{i}] ID={update['id']}")
        print(f"    旧: {update['old_title']}")
        print(f"    新: {update['new_title']}")
        print()

    if args.dry_run:
        print("=== DRY RUN 模式，未执行实际变更 ===")
        return

    # 执行变更
    print("开始执行变更...")
    success_count = 0
    fail_count = 0

    for update in updates:
        try:
            result = service.update_note(update['id'], title=update['new_title'])
            if result:
                success_count += 1
                print(f"  [OK] ID={update['id']}")
            else:
                fail_count += 1
                print(f"  [FAIL] ID={update['id']}: 更新返回 False")
        except Exception as e:
            fail_count += 1
            print(f"  [ERROR] ID={update['id']}: {e}")

    print(f"\n完成: 成功 {success_count} 条, 失败 {fail_count} 条")


if __name__ == "__main__":
    main()
