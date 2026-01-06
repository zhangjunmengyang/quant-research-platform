# -*- coding: utf-8 -*-
"""
临时脚本：清洗 factors 文件夹中所有因子代码
- 去掉所有三引号注释块 (docstrings)
- 去掉所有 # 注释行和行尾注释
"""
import re
from pathlib import Path


def remove_docstrings(content: str) -> str:
    """移除代码中的所有三引号注释块"""
    pattern = r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')'

    result = []
    last_end = 0

    for match in re.finditer(pattern, content):
        start, end = match.span()
        result.append(content[last_end:start])

        before = content[last_end:start]
        lines_before = before.split('\n')
        last_line = lines_before[-1] if lines_before else ''

        # 如果前面只有空白，说明是独立的注释块，删除它
        if last_line.strip() == '' or last_line.strip().startswith('#'):
            pass
        else:
            # 这可能是字符串赋值，保留
            result.append(match.group())

        last_end = end

    result.append(content[last_end:])
    return ''.join(result)


def remove_comments(content: str) -> str:
    """移除所有 # 注释（整行注释和行尾注释）"""
    lines = content.split('\n')
    cleaned_lines = []

    for line in lines:
        # 跳过纯注释行
        stripped = line.strip()
        if stripped.startswith('#'):
            continue

        # 处理行尾注释，需要注意字符串中的 #
        # 简单处理：找到不在字符串内的 #
        new_line = remove_inline_comment(line)

        cleaned_lines.append(new_line)

    return '\n'.join(cleaned_lines)


def remove_inline_comment(line: str) -> str:
    """移除行尾注释，保留字符串中的 #"""
    result = []
    in_string = False
    string_char = None
    i = 0

    while i < len(line):
        char = line[i]

        # 处理字符串
        if char in ('"', "'") and (i == 0 or line[i-1] != '\\'):
            if not in_string:
                in_string = True
                string_char = char
            elif char == string_char:
                in_string = False
                string_char = None
            result.append(char)
        elif char == '#' and not in_string:
            # 找到注释开始，截断并去除尾部空白
            return ''.join(result).rstrip()
        else:
            result.append(char)

        i += 1

    return ''.join(result)


def clean_content(content: str) -> str:
    """清洗文件内容"""
    # 1. 移除 docstrings
    content = remove_docstrings(content)

    # 2. 移除所有 # 注释
    content = remove_comments(content)

    # 3. 清理多余的空行
    content = content.lstrip('\n')
    content = re.sub(r'\n{3,}', '\n\n', content)

    # 4. 确保文件末尾有换行符
    if content and not content.endswith('\n'):
        content += '\n'

    return content


def process_file(file_path: Path) -> bool:
    """处理单个文件，返回是否有修改"""
    try:
        content = file_path.read_text(encoding='utf-8')
        cleaned = clean_content(content)

        if content != cleaned:
            file_path.write_text(cleaned, encoding='utf-8')
            return True
        return False
    except Exception as e:
        print(f"  错误处理 {file_path}: {e}")
        return False


def main():
    factors_dir = Path(__file__).parent.parent / 'factors'

    if not factors_dir.exists():
        print(f"目录不存在: {factors_dir}")
        return

    py_files = list(factors_dir.glob('**/*.py'))
    print(f"找到 {len(py_files)} 个 Python 文件")

    modified_count = 0
    for file_path in sorted(py_files):
        if process_file(file_path):
            print(f"  已清洗: {file_path.name}")
            modified_count += 1

    print(f"\n完成! 共修改 {modified_count} 个文件")


if __name__ == '__main__':
    main()
