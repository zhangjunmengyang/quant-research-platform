"""
进度报告器 - 实时进度显示和报告生成
"""

import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class StageStats:
    """阶段统计信息"""
    name: str
    total: int = 0
    completed: int = 0
    failed: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        """获取耗时（秒）"""
        if self.start_time is None:
            return 0
        end = self.end_time or time.time()
        return end - self.start_time

    @property
    def progress(self) -> float:
        """获取进度百分比"""
        if self.total == 0:
            return 0
        return (self.completed + self.failed) / self.total * 100


class ProgressReporter:
    """进度报告器"""

    def __init__(self, output=None, bar_width: int = 40):
        """
        初始化进度报告器

        Args:
            output: 输出流，默认 sys.stdout
            bar_width: 进度条宽度
        """
        self.output = output or sys.stdout
        self.bar_width = bar_width
        self.stages: List[StageStats] = []
        self.current_stage: Optional[StageStats] = None
        self.start_time: Optional[float] = None

    def start_pipeline(self):
        """开始 Pipeline"""
        self.start_time = time.time()
        self.stages = []
        self._print_header()

    def start_stage(self, stage_name: str, total: int):
        """
        开始一个阶段

        Args:
            stage_name: 阶段名称
            total: 总任务数
        """
        self.current_stage = StageStats(
            name=stage_name,
            total=total,
            start_time=time.time()
        )
        self.stages.append(self.current_stage)
        self._print_stage_start()

    def update(self, current: int, message: str = ""):
        """
        更新当前进度

        Args:
            current: 当前完成数
            message: 当前处理信息
        """
        if self.current_stage is None:
            return

        self.current_stage.completed = current
        self._print_progress(message)

    def increment(self, message: str = ""):
        """
        增加一个完成计数

        Args:
            message: 当前处理信息
        """
        if self.current_stage is None:
            return

        self.current_stage.completed += 1
        self._print_progress(message)

    def fail(self, message: str = ""):
        """
        记录一个失败

        Args:
            message: 失败信息
        """
        if self.current_stage is None:
            return

        self.current_stage.failed += 1
        self._print_progress(message, is_error=True)

    def finish_stage(self, summary: Optional[Dict[str, Any]] = None):
        """
        完成当前阶段

        Args:
            summary: 阶段汇总信息
        """
        if self.current_stage is None:
            return

        self.current_stage.end_time = time.time()
        if summary:
            self.current_stage.details = summary

        self._print_stage_end()
        self.current_stage = None

    def finish_pipeline(self) -> str:
        """
        完成 Pipeline 并生成报告

        Returns:
            Markdown 格式的报告
        """
        return self._generate_report()

    def _print_header(self):
        """打印头部"""
        self.output.write("\n")
        self.output.write("=" * 60 + "\n")
        self.output.write("              Factor Pipeline\n")
        self.output.write("=" * 60 + "\n")
        self.output.flush()

    def _print_stage_start(self):
        """打印阶段开始"""
        stage = self.current_stage
        self.output.write(f"\n▶ {stage.name} (共 {stage.total} 项)\n")
        self.output.write("-" * 60 + "\n")
        self.output.flush()

    def _print_progress(self, message: str = "", is_error: bool = False):
        """打印进度条"""
        stage = self.current_stage
        if stage is None:
            return

        # 计算进度
        done = stage.completed + stage.failed
        percent = stage.progress

        # 构建进度条
        filled = int(self.bar_width * done / stage.total) if stage.total > 0 else 0
        bar = "█" * filled + "░" * (self.bar_width - filled)

        # 计算速度和预计剩余时间
        elapsed = time.time() - stage.start_time
        speed = done / elapsed if elapsed > 0 else 0
        remaining = (stage.total - done) / speed if speed > 0 else 0

        # 状态指示
        status = "❌" if is_error else "✓"

        # 打印进度行
        line = f"\r[{bar}] {percent:5.1f}% ({done}/{stage.total})"
        if speed > 0:
            line += f" | {speed:.1f}/s | ETA: {self._format_time(remaining)}"
        if message:
            # 截断过长的消息
            max_msg_len = 30
            if len(message) > max_msg_len:
                message = message[:max_msg_len-3] + "..."
            line += f" | {status} {message}"

        self.output.write(line)
        self.output.flush()

    def _print_stage_end(self):
        """打印阶段结束"""
        stage = self.current_stage
        self.output.write("\n")
        self.output.write(f"✓ {stage.name} 完成: ")
        self.output.write(f"成功 {stage.completed}, 失败 {stage.failed}, ")
        self.output.write(f"耗时 {self._format_time(stage.duration)}\n")
        self.output.flush()

    def _format_time(self, seconds: float) -> str:
        """格式化时间"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"

    def _generate_report(self) -> str:
        """生成 Markdown 报告"""
        total_duration = time.time() - self.start_time if self.start_time else 0

        lines = [
            "# Factor Pipeline Report",
            "",
            "## 执行摘要",
            "",
            "| 项目 | 值 |",
            "|------|-----|",
            f"| 执行时间 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |",
            f"| 总耗时 | {self._format_time(total_duration)} |",
            f"| 执行阶段 | {' → '.join(s.name for s in self.stages)} |",
            "",
        ]

        # 每个阶段的详细信息
        for stage in self.stages:
            lines.extend([
                f"## {stage.name} 阶段",
                "",
                f"- 总数: {stage.total}",
                f"- 成功: {stage.completed}",
                f"- 失败: {stage.failed}",
                f"- 耗时: {self._format_time(stage.duration)}",
                "",
            ])

            # 添加阶段特定的详情
            if stage.details:
                for key, value in stage.details.items():
                    if isinstance(value, dict):
                        lines.append(f"### {key}")
                        lines.append("")
                        for k, v in value.items():
                            lines.append(f"- {k}: {v}")
                        lines.append("")
                    elif isinstance(value, list):
                        lines.append(f"### {key}")
                        lines.append("")
                        for item in value[:10]:  # 最多显示 10 项
                            lines.append(f"- {item}")
                        if len(value) > 10:
                            lines.append(f"- ... 等 {len(value) - 10} 项")
                        lines.append("")
                    else:
                        lines.append(f"- {key}: {value}")
                lines.append("")

        return "\n".join(lines)


# 单例实例
_progress_reporter: Optional[ProgressReporter] = None


def get_progress_reporter() -> ProgressReporter:
    """获取进度报告器单例"""
    global _progress_reporter
    if _progress_reporter is None:
        _progress_reporter = ProgressReporter()
    return _progress_reporter
