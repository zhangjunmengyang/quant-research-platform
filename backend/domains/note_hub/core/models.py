"""
研究笔记数据模型定义

Note Hub 定位为"研究草稿/临时记录"层（Knowledge Layer），
用于存储研究过程中的观察、假设和检验。
笔记可以被提炼为正式经验（Experience）。

研究流程：观察 -> 假设 -> 检验
- 观察：对数据或现象的客观记录
- 假设：基于观察提出的待验证假说
- 检验：对假设的验证过程和结论，关联到具体假设
"""

import uuid as uuid_lib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class NoteType(str, Enum):
    """
    笔记类型枚举

    研究流程：观察 -> 假设 -> 检验
    - observation: 观察 - 对数据或现象的客观记录
    - hypothesis: 假设 - 基于观察提出的待验证假说
    - verification: 检验 - 对假设的验证过程和结论
    """
    OBSERVATION = "observation"
    HYPOTHESIS = "hypothesis"
    VERIFICATION = "verification"


@dataclass
class Note:
    """
    研究笔记数据类

    作为研究过程中的临时记录，支持：
    - 分类管理：observation/hypothesis/verification
    - 关联关系：通过 Graph 系统 (graph_hub) 管理实体间关系
    - 提炼为经验：从笔记中提取正式经验

    Attributes:
        id: 笔记 ID（主键，自增）
        title: 笔记标题
        content: 笔记内容（Markdown 格式）
        tags: 标签（逗号分隔的字符串）

        note_type: 笔记类型（observation/hypothesis/verification）
        promoted_to_experience_id: 已提炼为经验的 ID（如果有）
        is_archived: 是否已归档

        created_at: 创建时间
        updated_at: 更新时间

    Note:
        实体间关联（如检验关联假设）通过 Edge 系统管理，使用:
        - link_note(note_id, target_type="note", target_id, relation="verifies")
        - get_note_edges(note_id)
        - trace_note_lineage(note_id)
    """
    id: int | None = None
    uuid: str = field(default_factory=lambda: str(uuid_lib.uuid4()))
    title: str = ""
    content: str = ""
    tags: str = ""
    source: str | None = None  # 来源类型（如 factor, strategy）
    source_ref: str | None = None  # 来源引用（如因子名、策略ID）

    note_type: str = field(default=NoteType.OBSERVATION.value)
    promoted_to_experience_id: int | None = None
    is_archived: bool = False

    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'title': self.title,
            'content': self.content,
            'tags': self.tags,
            'source': self.source,
            'source_ref': self.source_ref,
            'note_type': self.note_type,
            'promoted_to_experience_id': self.promoted_to_experience_id,
            'is_archived': self.is_archived,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Note':
        """从字典创建笔记实例"""
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)

    @property
    def tags_list(self) -> list[str]:
        """获取标签列表（逗号分隔的字符串转为列表）"""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    def set_tags(self, tags: list[str]):
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
            NoteType.VERIFICATION.value: "检验",
        }
        return labels.get(self.note_type, "笔记")
