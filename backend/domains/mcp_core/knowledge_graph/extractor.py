"""
知识图谱抽取器

基于 LLM 从文本中抽取实体和关系:
- EntityExtractor: 实体抽取
- RelationExtractor: 关系识别
- KnowledgeExtractor: 统一抽取接口

使用 mcp_core/llm 的 LLM 调用能力。
"""

import json
import logging
from typing import Any, Dict, List, Optional

from .models import (
    Entity,
    EntityType,
    Relation,
    RelationType,
    Triple,
    ENTITY_TYPE_NAMES,
    RELATION_TYPE_NAMES,
)

logger = logging.getLogger(__name__)


# ============================================
# Prompt 模板
# ============================================

ENTITY_EXTRACTION_SYSTEM_PROMPT = """你是一个专业的量化研究知识抽取助手。你的任务是从文本中识别和抽取实体。

实体类型说明:
{entity_types}

输出要求:
1. 输出 JSON 格式的实体列表
2. 每个实体包含: name(名称), type(类型), properties(属性字典)
3. properties 可以包含: description(描述), aliases(别名), importance(重要性0-1)
4. 只抽取与量化交易/因子研究相关的实体
5. 确保实体名称规范化（如 "动量因子" 而非 "momentum"）

输出格式:
```json
{{
  "entities": [
    {{
      "name": "实体名称",
      "type": "实体类型",
      "properties": {{
        "description": "实体描述",
        "aliases": ["别名1", "别名2"],
        "importance": 0.8
      }}
    }}
  ]
}}
```"""

ENTITY_EXTRACTION_USER_PROMPT = """请从以下文本中抽取实体:

---
{text}
---

请输出 JSON 格式的实体列表。"""


RELATION_EXTRACTION_SYSTEM_PROMPT = """你是一个专业的量化研究知识抽取助手。你的任务是识别实体之间的关系。

关系类型说明:
{relation_types}

已知实体:
{entities}

输出要求:
1. 输出 JSON 格式的关系列表
2. 每个关系包含: subject(主语), predicate(关系类型), object(宾语), confidence(置信度0-1)
3. subject 和 object 必须是已知实体中的名称
4. predicate 必须是支持的关系类型之一
5. 只抽取文本中明确支持的关系

输出格式:
```json
{{
  "relations": [
    {{
      "subject": "实体A",
      "predicate": "关系类型",
      "object": "实体B",
      "confidence": 0.9
    }}
  ]
}}
```"""

RELATION_EXTRACTION_USER_PROMPT = """请从以下文本中识别实体之间的关系:

---
{text}
---

请输出 JSON 格式的关系列表。"""


TRIPLE_EXTRACTION_SYSTEM_PROMPT = """你是一个专业的量化研究知识抽取助手。你的任务是从文本中抽取知识三元组（主语-谓语-宾语）。

实体类型说明:
{entity_types}

关系类型说明:
{relation_types}

输出要求:
1. 输出 JSON 格式的三元组列表
2. 每个三元组包含:
   - subject: 主语实体名称
   - subject_type: 主语实体类型
   - predicate: 关系类型
   - object: 宾语实体名称
   - object_type: 宾语实体类型
   - confidence: 置信度(0-1)
   - context: 支持这个关系的原文片段
3. 只抽取文本中明确支持的三元组
4. 确保实体类型和关系类型使用正确的枚举值

输出格式:
```json
{{
  "triples": [
    {{
      "subject": "动量因子",
      "subject_type": "factor",
      "predicate": "effective_in",
      "object": "牛市",
      "object_type": "market_regime",
      "confidence": 0.9,
      "context": "动量因子在牛市环境中表现优异"
    }}
  ]
}}
```"""

TRIPLE_EXTRACTION_USER_PROMPT = """请从以下文本中抽取知识三元组:

---
{text}
---

请输出 JSON 格式的三元组列表。"""


# ============================================
# 抽取器实现
# ============================================

class EntityExtractor:
    """
    实体抽取器

    使用 LLM 从文本中抽取实体。

    Example:
        from domains.mcp_core.llm import get_llm_client
        from domains.mcp_core.knowledge_graph import EntityExtractor

        extractor = EntityExtractor(get_llm_client())
        entities = await extractor.extract("动量因子在牛市中表现优异")
    """

    def __init__(
        self,
        llm_client: Any,
        model_key: Optional[str] = None,
        temperature: float = 0.0,
    ):
        """
        初始化实体抽取器

        Args:
            llm_client: LLM 客户端（from mcp_core.llm）
            model_key: 模型 key
            temperature: 温度参数
        """
        self.llm_client = llm_client
        self.model_key = model_key
        self.temperature = temperature

    def _build_entity_types_prompt(self) -> str:
        """构建实体类型说明"""
        lines = []
        for entity_type in EntityType:
            name = ENTITY_TYPE_NAMES.get(entity_type, entity_type.value)
            lines.append(f"- {entity_type.value}: {name}")
        return "\n".join(lines)

    async def extract(self, text: str) -> List[Entity]:
        """
        从文本中抽取实体

        Args:
            text: 输入文本

        Returns:
            实体列表
        """
        if not text.strip():
            return []

        entity_types = self._build_entity_types_prompt()
        system_prompt = ENTITY_EXTRACTION_SYSTEM_PROMPT.format(
            entity_types=entity_types
        )
        user_prompt = ENTITY_EXTRACTION_USER_PROMPT.format(text=text)

        try:
            response = await self.llm_client.ainvoke(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model_key=self.model_key,
                temperature=self.temperature,
                caller="EntityExtractor",
                purpose="extract_entities",
            )

            return self._parse_entity_response(response)

        except Exception as e:
            logger.error(f"实体抽取失败: {e}")
            return []

    def _parse_entity_response(self, response: str) -> List[Entity]:
        """解析 LLM 响应"""
        try:
            # 尝试提取 JSON 块
            json_str = self._extract_json(response)
            data = json.loads(json_str)

            entities = []
            for item in data.get("entities", []):
                entity_type_str = item.get("type", "concept")
                try:
                    entity_type = EntityType(entity_type_str)
                except ValueError:
                    entity_type = EntityType.CONCEPT

                entity = Entity(
                    entity_type=entity_type,
                    name=item.get("name", ""),
                    properties=item.get("properties", {}),
                    source_type="llm_extracted",
                )
                if entity.name:
                    entities.append(entity)

            return entities

        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}, 响应: {response[:200]}")
            return []

    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON 块"""
        # 尝试找到 ```json ... ``` 块
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()

        # 尝试找到 {...} 块
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return text[start:end]

        return text

    async def extract_batch(
        self,
        texts: List[str],
        batch_size: int = 5,
    ) -> List[List[Entity]]:
        """
        批量抽取实体

        Args:
            texts: 文本列表
            batch_size: 批次大小

        Returns:
            每个文本对应的实体列表
        """
        results = []
        for text in texts:
            entities = await self.extract(text)
            results.append(entities)
        return results


class RelationExtractor:
    """
    关系抽取器

    使用 LLM 识别实体之间的关系。

    Example:
        extractor = RelationExtractor(get_llm_client())
        relations = await extractor.extract(
            text="动量因子在牛市中表现优异",
            entities=[entity1, entity2]
        )
    """

    def __init__(
        self,
        llm_client: Any,
        model_key: Optional[str] = None,
        temperature: float = 0.0,
    ):
        """
        初始化关系抽取器

        Args:
            llm_client: LLM 客户端
            model_key: 模型 key
            temperature: 温度参数
        """
        self.llm_client = llm_client
        self.model_key = model_key
        self.temperature = temperature

    def _build_relation_types_prompt(self) -> str:
        """构建关系类型说明"""
        lines = []
        for relation_type in RelationType:
            name = RELATION_TYPE_NAMES.get(relation_type, relation_type.value)
            lines.append(f"- {relation_type.value}: {name}")
        return "\n".join(lines)

    def _build_entities_prompt(self, entities: List[Entity]) -> str:
        """构建实体列表说明"""
        lines = []
        for entity in entities:
            type_name = ENTITY_TYPE_NAMES.get(entity.entity_type, entity.entity_type.value)
            lines.append(f"- {entity.name} ({type_name})")
        return "\n".join(lines)

    async def extract(
        self,
        text: str,
        entities: List[Entity],
    ) -> List[Dict[str, Any]]:
        """
        从文本中识别实体之间的关系

        Args:
            text: 输入文本
            entities: 已知实体列表

        Returns:
            关系列表（字典格式，包含 subject, predicate, object, confidence）
        """
        if not text.strip() or len(entities) < 2:
            return []

        relation_types = self._build_relation_types_prompt()
        entities_prompt = self._build_entities_prompt(entities)

        system_prompt = RELATION_EXTRACTION_SYSTEM_PROMPT.format(
            relation_types=relation_types,
            entities=entities_prompt,
        )
        user_prompt = RELATION_EXTRACTION_USER_PROMPT.format(text=text)

        try:
            response = await self.llm_client.ainvoke(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model_key=self.model_key,
                temperature=self.temperature,
                caller="RelationExtractor",
                purpose="extract_relations",
            )

            return self._parse_relation_response(response, entities)

        except Exception as e:
            logger.error(f"关系抽取失败: {e}")
            return []

    def _parse_relation_response(
        self,
        response: str,
        entities: List[Entity],
    ) -> List[Dict[str, Any]]:
        """解析 LLM 响应"""
        try:
            json_str = self._extract_json(response)
            data = json.loads(json_str)

            # 构建实体名称到实体的映射
            entity_map = {e.name: e for e in entities}

            relations = []
            for item in data.get("relations", []):
                subject = item.get("subject", "")
                object_ = item.get("object", "")
                predicate = item.get("predicate", "related_to")
                confidence = item.get("confidence", 1.0)

                # 验证实体存在
                if subject not in entity_map or object_ not in entity_map:
                    continue

                # 验证关系类型
                try:
                    RelationType(predicate)
                except ValueError:
                    predicate = "related_to"

                relations.append({
                    "subject": subject,
                    "predicate": predicate,
                    "object": object_,
                    "confidence": confidence,
                    "subject_entity": entity_map[subject],
                    "object_entity": entity_map[object_],
                })

            return relations

        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}")
            return []

    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON 块"""
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()

        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return text[start:end]

        return text


class KnowledgeExtractor:
    """
    知识抽取器

    统一的接口，一次性抽取实体和关系，返回三元组。

    Example:
        extractor = KnowledgeExtractor(get_llm_client())
        triples = await extractor.extract("动量因子在牛市中表现优异")
    """

    def __init__(
        self,
        llm_client: Any,
        model_key: Optional[str] = None,
        temperature: float = 0.0,
    ):
        """
        初始化知识抽取器

        Args:
            llm_client: LLM 客户端
            model_key: 模型 key
            temperature: 温度参数
        """
        self.llm_client = llm_client
        self.model_key = model_key
        self.temperature = temperature
        self.entity_extractor = EntityExtractor(llm_client, model_key, temperature)
        self.relation_extractor = RelationExtractor(llm_client, model_key, temperature)

    def _build_entity_types_prompt(self) -> str:
        """构建实体类型说明"""
        lines = []
        for entity_type in EntityType:
            name = ENTITY_TYPE_NAMES.get(entity_type, entity_type.value)
            lines.append(f"- {entity_type.value}: {name}")
        return "\n".join(lines)

    def _build_relation_types_prompt(self) -> str:
        """构建关系类型说明"""
        lines = []
        for relation_type in RelationType:
            name = RELATION_TYPE_NAMES.get(relation_type, relation_type.value)
            lines.append(f"- {relation_type.value}: {name}")
        return "\n".join(lines)

    async def extract(self, text: str) -> List[Triple]:
        """
        从文本中抽取知识三元组

        使用一次 LLM 调用完成实体和关系的抽取。

        Args:
            text: 输入文本

        Returns:
            三元组列表
        """
        if not text.strip():
            return []

        entity_types = self._build_entity_types_prompt()
        relation_types = self._build_relation_types_prompt()

        system_prompt = TRIPLE_EXTRACTION_SYSTEM_PROMPT.format(
            entity_types=entity_types,
            relation_types=relation_types,
        )
        user_prompt = TRIPLE_EXTRACTION_USER_PROMPT.format(text=text)

        try:
            response = await self.llm_client.ainvoke(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model_key=self.model_key,
                temperature=self.temperature,
                caller="KnowledgeExtractor",
                purpose="extract_triples",
            )

            return self._parse_triple_response(response)

        except Exception as e:
            logger.error(f"三元组抽取失败: {e}")
            return []

    def _parse_triple_response(self, response: str) -> List[Triple]:
        """解析 LLM 响应"""
        try:
            json_str = self._extract_json(response)
            data = json.loads(json_str)

            triples = []
            for item in data.get("triples", []):
                try:
                    triple = Triple.from_dict(item)
                    if triple.subject and triple.object:
                        triples.append(triple)
                except Exception as e:
                    logger.warning(f"三元组解析失败: {e}, 数据: {item}")

            return triples

        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}")
            return []

    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON 块"""
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()

        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return text[start:end]

        return text

    async def extract_with_entities(
        self,
        text: str,
    ) -> tuple[List[Entity], List[Relation]]:
        """
        从文本中抽取实体和关系

        分两步进行：先抽取实体，再抽取关系。

        Args:
            text: 输入文本

        Returns:
            (实体列表, 关系列表)
        """
        # 先抽取实体
        entities = await self.entity_extractor.extract(text)
        if len(entities) < 2:
            return entities, []

        # 再抽取关系
        relation_dicts = await self.relation_extractor.extract(text, entities)

        # 转换关系格式
        # 注意: 此时实体尚未持久化，没有有效的数据库 ID
        # 关系的 source_id/target_id 使用临时值 0，需要在持久化后更新
        relations = []
        entity_map = {e.name: e for e in entities}
        for rd in relation_dicts:
            subject_entity = entity_map.get(rd["subject"])
            object_entity = entity_map.get(rd["object"])
            if subject_entity and object_entity:
                relation = Relation(
                    relation_type=RelationType(rd["predicate"]),
                    source_id=subject_entity.id if subject_entity.id is not None else 0,
                    target_id=object_entity.id if object_entity.id is not None else 0,
                    properties={
                        "confidence": rd.get("confidence", 1.0),
                        "subject_name": subject_entity.name,
                        "object_name": object_entity.name,
                    },
                )
                relations.append(relation)

        return entities, relations

    async def extract_batch(
        self,
        texts: List[str],
    ) -> List[List[Triple]]:
        """
        批量抽取三元组

        Args:
            texts: 文本列表

        Returns:
            每个文本对应的三元组列表
        """
        results = []
        for text in texts:
            triples = await self.extract(text)
            results.append(triples)
        return results
