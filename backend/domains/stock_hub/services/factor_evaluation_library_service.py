"""因子评估库服务 - 管理因子评估记录的保存、查询和更新。"""

from __future__ import annotations

import logging
from typing import Any

from domains.stock_hub.core.factor_evaluation_models import (
    FactorEvaluation,
    FactorEvaluationContent,
)
from domains.stock_hub.core.factor_evaluation_store import get_factor_evaluation_store

logger = logging.getLogger(__name__)


class FactorEvaluationLibraryService:
    """因子评估库服务。"""

    def __init__(self) -> None:
        self._store = get_factor_evaluation_store()
        self._store.init_schema()

    def save(
        self,
        factor_name: str,
        title: str,
        evaluations: dict[str, str],
        analysis_snapshot: dict[str, Any],
        tags: list[str] | None = None,
    ) -> FactorEvaluation:
        """保存因子评估到库。"""
        evaluation = FactorEvaluation(
            factor_name=factor_name,
            title=title,
            content=FactorEvaluationContent(
                evaluations=evaluations,
                analysis_snapshot=analysis_snapshot,
            ),
            tags=tags or [],
        )
        new_id = self._store.add(evaluation)
        if new_id is None:
            raise RuntimeError("保存因子评估失败")
        evaluation.id = new_id
        return evaluation

    def get(self, uuid: str) -> FactorEvaluation | None:
        """获取单条因子评估。"""
        return self._store.get_by_uuid(uuid)

    def update(self, uuid: str, **fields) -> bool:
        """更新因子评估。

        Supported fields: title, evaluations (dict), tags (list)
        """
        ev = self._store.get_by_uuid(uuid)
        if not ev:
            return False

        update_kwargs: dict[str, Any] = {}
        if "title" in fields and fields["title"] is not None:
            update_kwargs["title"] = fields["title"]
        if "evaluations" in fields and fields["evaluations"] is not None:
            # Merge evaluations into existing content
            new_content = FactorEvaluationContent(
                evaluations=fields["evaluations"],
                analysis_snapshot=ev.content.analysis_snapshot,
            )
            update_kwargs["content"] = new_content
        if "tags" in fields and fields["tags"] is not None:
            import json
            update_kwargs["tags"] = json.dumps(fields["tags"], ensure_ascii=False)

        if not update_kwargs:
            return False
        return self._store.update(ev.id, **update_kwargs)

    def delete(self, uuid: str) -> bool:
        """删除因子评估。"""
        return self._store.delete_by_uuid(uuid)

    def list(
        self,
        factor_name: str | None = None,
        tags: list[str] | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[FactorEvaluation], int]:
        """列表查询因子评估。"""
        offset = (page - 1) * page_size
        return self._store.query(
            factor_name=factor_name,
            tags=tags,
            search=search,
            limit=page_size,
            offset=offset,
        )

    def get_all_tags(self) -> list[str]:
        """获取所有标签。"""
        return self._store.get_all_tags()


_service_instance: FactorEvaluationLibraryService | None = None


def get_factor_evaluation_library_service() -> FactorEvaluationLibraryService:
    """获取评估库服务单例。"""
    global _service_instance
    if _service_instance is None:
        _service_instance = FactorEvaluationLibraryService()
    return _service_instance
