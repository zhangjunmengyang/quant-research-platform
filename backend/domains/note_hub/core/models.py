"""
研究笔记数据模型定义

Note Hub 定位为"研究草稿/临时记录"层（Knowledge Layer），
用于存储研究过程中的观察、假设、发现和研究轨迹。
笔记可以被提炼为正式经验（Experience）。
"""

import uuid as uuid_lib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List


class NoteType(str, Enum):
    """
    笔记类型枚举

    - observation: 观察 - 对数据或现象的客观记录
    - hypothesis: 假设 - 基于观察提出的假设
    - finding: 发现 - 验证后的发现
    - trail: 轨迹 - 研究过程记录（自动生成）
    - general: 通用 - 一般性笔记（向后兼容）
    """
    OBSERVATION = "observation"
    HYPOTHESIS = "hypothesis"
    FINDING = "finding"
    TRAIL = "trail"
    GENERAL = "general"


@dataclass
class Note:
    """
    研究笔记数据类

    作为研究过程中的临时记录，支持：
    - 分类管理：observation/hypothesis/finding/trail
    - 研究会话关联：追踪研究轨迹
    - 提炼为经验：从笔记中提取正式经验

    Attributes:
        id: 笔记 ID（主键，自增）
        title: 笔记标题
        content: 笔记内容（Markdown 格式）
        tags: 标签（逗号分隔的字符串）

        note_type: 笔记类型（observation/hypothesis/finding/trail/general）
        research_session_id: 研究会话 ID，用于追踪研究轨迹
        promoted_to_experience_id: 已提炼为经验的 ID（如果有）
        is_archived: 是否已归档

        created_at: 创建时间
        updated_at: 更新时间
    """
    id: Optional[int] = None
    uuid: str = field(default_factory=lambda: str(uuid_lib.uuid4()))
    title: str = ""
    content: str = ""
    tags: str = ""

    note_type: str = field(default=NoteType.GENERAL.value)
    research_session_id: Optional[str] = None
    promoted_to_experience_id: Optional[int] = None
    is_archived: bool = False

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'title': self.title,
            'content': self.content,
            'tags': self.tags,
            'note_type': self.note_type,
            'research_session_id': self.research_session_id,
            'promoted_to_experience_id': self.promoted_to_experience_id,
            'is_archived': self.is_archived,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Note':
        """从字典创建笔记实例"""
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)

    @property
    def tags_list(self) -> List[str]:
        """获取标签列表（逗号分隔的字符串转为列表）"""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    def set_tags(self, tags: List[str]):
        """设置标签列表"""
        self.tags = ','.join(tags)

    def add_tag(self, tag: str):
        """添加标签"""
        tags = self.tags_list
        if tag not in tags:
            tags.append(tag)
            self.set_tags(tags)

    def remove_tag(self, tag: str):
        """移除标签"""
        tags = self.tags_list
        if tag in tags:
            tags.remove(tag)
            self.set_tags(tags)

    @property
    def summary(self) -> str:
        """获取内容摘要（前 200 字符）"""
        if not self.content:
            return ""
        content = self.content.strip()
        if len(content) <= 200:
            return content
        return content[:200] + "..."

    @property
    def is_promoted(self) -> bool:
        """是否已提炼为经验"""
        return self.promoted_to_experience_id is not None

    @property
    def type_label(self) -> str:
        """获取类型的中文标签"""
        labels = {
            NoteType.OBSERVATION.value: "观察",
            NoteType.HYPOTHESIS.value: "假设",
            NoteType.FINDING.value: "发现",
            NoteType.TRAIL.value: "轨迹",
            NoteType.GENERAL.value: "笔记",
        }
        return labels.get(self.note_type, "笔记")
