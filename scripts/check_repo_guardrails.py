"""仓库级 guardrail 检查。

主要用于在 PR 阶段尽早拦截两类高频问题：
1. 明文密钥/Token 直接入仓
2. 作者本机绝对路径混入源码、配置或文档
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TEXT_EXTENSIONS = {
    ".md",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".sh",
}
SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "backups",
}

SECRET_PATTERNS = [
    (
        re.compile(r"\bcr_[A-Fa-f0-9]{32,}\b"),
        "疑似中转服务密钥",
    ),
    (
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
        "疑似 GitHub Token",
    ),
    (
        re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
        "疑似 OpenAI 风格密钥",
    ),
    (
        re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
        "疑似 Slack Token",
    ),
]

PATH_PATTERNS = [
    (
        re.compile(r"(?<![A-Za-z])/(Users|home)/[^/\s]+/"),
        "疑似 Unix 本机绝对路径",
    ),
    (
        re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\s]+\\\\"),
        "疑似 Windows 本机绝对路径",
    ),
]

ALLOWLIST_SUBSTRINGS = {
    "LLM_API_KEY",
    "OPENAI_API_KEY",
    "YOUR_API_KEY",
    "example_key",
    "token scopes",
}


def should_scan(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    return path.suffix in TEXT_EXTENSIONS


def is_allowed(line: str) -> bool:
    return any(marker in line for marker in ALLOWLIST_SUBSTRINGS)


def scan_file(path: Path) -> list[str]:
    issues: list[str] = []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        issues.append(f"{path}: 读取失败: {exc}")
        return issues

    for lineno, line in enumerate(content.splitlines(), start=1):
        if is_allowed(line):
            continue
        for pattern, label in SECRET_PATTERNS + PATH_PATTERNS:
            match = pattern.search(line)
            if match:
                issues.append(
                    f"{path.relative_to(ROOT)}:{lineno}: {label}: {match.group(0)}"
                )
                break
    return issues


def iter_scan_paths(cli_args: list[str]) -> list[Path]:
    """根据命令行参数决定扫描范围。"""
    if not cli_args:
        return [path for path in ROOT.rglob("*") if path.is_file()]

    selected_paths: list[Path] = []
    for raw_path in cli_args:
        path = (ROOT / raw_path).resolve()
        if path.is_file():
            selected_paths.append(path)
    return selected_paths


def main() -> int:
    issues: list[str] = []
    for path in iter_scan_paths(sys.argv[1:]):
        if should_scan(path):
            issues.extend(scan_file(path))

    if issues:
        print("发现仓库 guardrail 问题：")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("仓库 guardrail 检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
