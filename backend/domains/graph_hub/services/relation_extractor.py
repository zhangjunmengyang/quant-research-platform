"""
关系解析器

从内容中提取实体引用，支持:
1. 规则匹配: 正则提取因子名、策略ID等
2. 已知因子列表精确匹配
"""

import re
from dataclasses import dataclass


@dataclass
class ExtractedRelation:
    """提取的关系"""

    target_type: str  # factor / strategy / note
    target_id: str
    relation: str  # derives / relates
    subtype: str  # refs / uses / ...
    confidence: float  # 置信度 0-1
    context: str = ""  # 匹配上下文


class RelationExtractor:
    """
    关系解析器

    从文本内容中提取实体引用，支持因子名、策略UUID等。
    """

    # 因子名模式: 大驼峰命名 + 可选后缀
    # 示例: MomentumFactor, Volatility_5d, PriceChange_24H
    FACTOR_PATTERN = re.compile(
        r"\b([A-Z][a-z]+(?:[A-Z][a-z0-9]+)+(?:_\d+[dDhHmM]?)?)\b"
    )

    # 策略 UUID 模式
    STRATEGY_UUID_PATTERN = re.compile(
        r"\b([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b",
        re.IGNORECASE,
    )

    # 笔记引用模式: #note-123 或 [[note:123]]
    NOTE_REF_PATTERN = re.compile(r"(?:#note-|(?:\[\[note:))(\d+)(?:\]\])?")

    def __init__(self, known_factors: list[str] | None = None):
        """
        初始化

        Args:
            known_factors: 已知因子名列表，用于精确匹配提高置信度
        """
        self.known_factors = set(known_factors or [])

    def extract_from_text(self, content: str) -> list[ExtractedRelation]:
        """
        从文本中提取关系

        Args:
            content: 文本内容

        Returns:
            提取的关系列表
        """
        relations = []
        seen = set()  # 去重

        # 1. 提取因子引用
        for match in self.FACTOR_PATTERN.finditer(content):
            factor_name = match.group(1)

            # 跳过常见的非因子词
            if factor_name in {"BaseModel", "DataFrame", "NoteType", "NodeType"}:
                continue

            # 去重
            key = ("factor", factor_name)
            if key in seen:
                continue
            seen.add(key)

            # 置信度: 已知因子 = 1.0, 未知因子 = 0.6
            confidence = 1.0 if factor_name in self.known_factors else 0.6

            # 提取上下文 (前后各50字符)
            start = max(0, match.start() - 50)
            end = min(len(content), match.end() + 50)
            context = content[start:end].replace("\n", " ")

            relations.append(
                ExtractedRelation(
                    target_type="factor",
                    target_id=factor_name,
                    relation="relates",
                    subtype="refs",
                    confidence=confidence,
                    context=context,
                )
            )

        # 2. 提取策略引用
        for match in self.STRATEGY_UUID_PATTERN.finditer(content):
            strategy_id = match.group(1).lower()

            key = ("strategy", strategy_id)
            if key in seen:
                continue
            seen.add(key)

            start = max(0, match.start() - 50)
            end = min(len(content), match.end() + 50)
            context = content[start:end].replace("\n", " ")

            relations.append(
                ExtractedRelation(
                    target_type="strategy",
                    target_id=strategy_id,
                    relation="relates",
                    subtype="refs",
                    confidence=0.9,
                    context=context,
                )
            )

        # 3. 提取笔记引用
        for match in self.NOTE_REF_PATTERN.finditer(content):
            note_id = match.group(1)

            key = ("note", note_id)
            if key in seen:
                continue
            seen.add(key)

            start = max(0, match.start() - 50)
            end = min(len(content), match.end() + 50)
            context = content[start:end].replace("\n", " ")

            relations.append(
                ExtractedRelation(
                    target_type="note",
                    target_id=note_id,
                    relation="relates",
                    subtype="refs",
                    confidence=1.0,
                    context=context,
                )
            )

        return relations

    def extract_from_backtest(
        self,
        strategy_list: list[dict],
    ) -> list[ExtractedRelation]:
        """
        从回测配置中提取关系

        Args:
            strategy_list: 策略配置列表

        Returns:
            提取的关系列表 (策略 -> 因子)
        """
        relations = []
        seen = set()

        for stg in strategy_list:
            # 主因子
            factor_list = stg.get("factor_list", [])
            for factor_item in factor_list:
                if isinstance(factor_item, (list, tuple)):
                    factor_name = factor_item[0]
                else:
                    factor_name = str(factor_item)

                key = ("factor", factor_name, "main")
                if key in seen:
                    continue
                seen.add(key)

                relations.append(
                    ExtractedRelation(
                        target_type="factor",
                        target_id=factor_name,
                        relation="derives",
                        subtype="uses",
                        confidence=1.0,
                        context="factor_list",
                    )
                )

            # 过滤因子
            filter_keys = [
                "filter_list",
                "long_filter_list",
                "short_filter_list",
                "filter_list_post",
                "long_filter_list_post",
                "short_filter_list_post",
            ]
            for filter_key in filter_keys:
                for filter_item in stg.get(filter_key, []):
                    if isinstance(filter_item, (list, tuple)):
                        filter_name = filter_item[0]
                    else:
                        filter_name = str(filter_item)

                    key = ("factor", filter_name, filter_key)
                    if key in seen:
                        continue
                    seen.add(key)

                    relations.append(
                        ExtractedRelation(
                            target_type="factor",
                            target_id=filter_name,
                            relation="derives",
                            subtype="uses",
                            confidence=1.0,
                            context=filter_key,
                        )
                    )

        return relations


# 单例
_extractor: RelationExtractor | None = None


def get_relation_extractor(
    known_factors: list[str] | None = None,
) -> RelationExtractor:
    """获取关系解析器实例"""
    global _extractor
    if _extractor is None or known_factors is not None:
        _extractor = RelationExtractor(known_factors)
    return _extractor
