"""
Graph API 路由

提供知识图谱的 REST API 端点。
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas.common import ApiResponse
from app.schemas.graph import (
    CreateLinkRequest,
    CreateLinkResponse,
    CypherQueryRequest,
    CypherQueryResponse,
    GetEdgesResponse,
    GraphEdge,
    GraphNode,
    GraphNodeType,
    GraphOverviewEdge,
    GraphOverviewResponse,
    GraphOverviewStats,
    GraphRelationType,
    LineageResult,
    PathResult,
    TagInfo,
    TaggedEntity,
    EntityTagsResponse,
)
from domains.graph_hub.services.graph_service import get_graph_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/edges", response_model=ApiResponse[GetEdgesResponse])
async def get_edges(
    entity_type: GraphNodeType = Query(..., description="实体类型"),
    entity_id: str = Query(..., description="实体 ID"),
    include_bidirectional: bool = Query(True, description="是否包含双向关系"),
):
    """
    获取实体的所有关联边

    返回指定实体的所有出边，可选择是否包含双向关系的反向边。
    """
    service = get_graph_service()
    success, message, edges = service.get_edges(
        entity_type=entity_type.value,
        entity_id=entity_id,
        include_bidirectional=include_bidirectional,
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return ApiResponse(
        data=GetEdgesResponse(
            entity_type=entity_type,
            entity_id=entity_id,
            count=len(edges),
            edges=[GraphEdge(**e) for e in edges],
        )
    )


@router.post("/links", response_model=ApiResponse[CreateLinkResponse])
async def create_link(request: CreateLinkRequest):
    """
    创建实体间的关联

    创建从源实体到目标实体的关系边。

    关系类型:
    - derives: 派生关系（有方向），subtype: based/inspired/uses/produces/evolves/enables
    - relates: 关联关系（默认双向），subtype: refs/similar/validates/contrasts/temporal
    """
    service = get_graph_service()
    success, message = service.create_link(
        source_type=request.source_type.value,
        source_id=request.source_id,
        target_type=request.target_type.value,
        target_id=request.target_id,
        relation=request.relation.value,
        subtype=request.subtype,
        is_bidirectional=request.is_bidirectional,
        metadata=request.metadata,
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return ApiResponse(data=CreateLinkResponse(message=message))


@router.delete("/links", response_model=ApiResponse[CreateLinkResponse])
async def delete_link(
    source_type: GraphNodeType = Query(..., description="源实体类型"),
    source_id: str = Query(..., description="源实体 ID"),
    target_type: GraphNodeType = Query(..., description="目标实体类型"),
    target_id: str = Query(..., description="目标实体 ID"),
    relation: GraphRelationType = Query(..., description="关系类型"),
):
    """
    删除实体间的关联

    删除指定的关系边。
    """
    service = get_graph_service()
    success, message = service.delete_link(
        source_type=source_type.value,
        source_id=source_id,
        target_type=target_type.value,
        target_id=target_id,
        relation=relation.value,
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return ApiResponse(data=CreateLinkResponse(message=message))


@router.get("/lineage", response_model=ApiResponse[LineageResult])
async def trace_lineage(
    entity_type: GraphNodeType = Query(..., description="实体类型"),
    entity_id: str = Query(..., description="实体 ID"),
    direction: str = Query("backward", description="追溯方向: backward(向上) 或 forward(向下)"),
    max_depth: int = Query(5, ge=1, le=10, description="最大深度"),
):
    """
    追溯知识链路

    - backward: 向上追溯源头（实体依赖什么）
    - forward: 向下追溯影响（什么依赖该实体）
    """
    service = get_graph_service()
    success, message, result = service.trace_lineage(
        entity_type=entity_type.value,
        entity_id=entity_id,
        direction=direction,
        max_depth=max_depth,
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return ApiResponse(data=LineageResult(**result))


@router.get("/path", response_model=ApiResponse[PathResult])
async def find_path(
    source_type: GraphNodeType = Query(..., description="源实体类型"),
    source_id: str = Query(..., description="源实体 ID"),
    target_type: GraphNodeType = Query(..., description="目标实体类型"),
    target_id: str = Query(..., description="目标实体 ID"),
    max_depth: int = Query(5, ge=1, le=10, description="最大深度"),
):
    """
    查找两实体间最短路径

    发现两个实体之间的间接关联。
    """
    service = get_graph_service()
    success, message, result = service.find_path(
        source_type=source_type.value,
        source_id=source_id,
        target_type=target_type.value,
        target_id=target_id,
        max_depth=max_depth,
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return ApiResponse(data=PathResult(**result))


@router.get("/tags", response_model=ApiResponse[EntityTagsResponse])
async def get_entity_tags(
    entity_type: GraphNodeType = Query(..., description="实体类型"),
    entity_id: str = Query(..., description="实体 ID"),
):
    """
    获取实体的所有标签
    """
    service = get_graph_service()
    success, message, tags = service.get_entity_tags(
        entity_type=entity_type.value,
        entity_id=entity_id,
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return ApiResponse(
        data=EntityTagsResponse(
            entity_type=entity_type,
            entity_id=entity_id,
            tags=tags,
            count=len(tags),
        )
    )


@router.get("/tags/all", response_model=ApiResponse[List[TagInfo]])
async def list_all_tags():
    """
    列出所有使用过的标签

    返回按使用频次降序排列的标签列表。
    """
    service = get_graph_service()
    success, message, tags = service.list_all_tags()

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return ApiResponse(data=[TagInfo(**t) for t in tags])


@router.get("/tags/{tag}/entities", response_model=ApiResponse[List[TaggedEntity]])
async def get_entities_by_tag(
    tag: str,
    entity_type: Optional[GraphNodeType] = Query(None, description="按实体类型筛选"),
):
    """
    获取拥有指定标签的所有实体
    """
    service = get_graph_service()
    success, message, entities = service.get_entities_by_tag(
        tag=tag,
        entity_type=entity_type.value if entity_type else None,
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return ApiResponse(data=[TaggedEntity(**e) for e in entities])


@router.get("/overview", response_model=ApiResponse[GraphOverviewResponse])
async def get_overview(
    node_limit: int = Query(500, ge=1, le=2000, description="节点数量限制"),
    edge_limit: int = Query(1000, ge=1, le=5000, description="边数量限制"),
):
    """
    获取图谱概览

    返回全量图谱数据 (带数量限制)，按节点连接度排序。
    适用于初始加载和全局视图。
    """
    service = get_graph_service()
    success, message, result = service.get_overview(node_limit, edge_limit)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return ApiResponse(
        data=GraphOverviewResponse(
            nodes=[GraphNode(**n) for n in result["nodes"]],
            edges=[GraphOverviewEdge(**e) for e in result["edges"]],
            stats=GraphOverviewStats(**result["stats"]),
        )
    )


@router.post("/cypher", response_model=ApiResponse[CypherQueryResponse])
async def execute_cypher(request: CypherQueryRequest):
    """
    执行只读 Cypher 查询

    仅支持只读操作 (MATCH, RETURN, WHERE 等)。
    禁止写操作 (CREATE, DELETE, SET 等)。

    示例查询:
    - MATCH (n) RETURN n LIMIT 100
    - MATCH (n:Factor)-[r]->(m) RETURN n, r, m
    """
    service = get_graph_service()
    success, message, result = service.execute_cypher(
        query=request.query,
        params=request.params,
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return ApiResponse(
        data=CypherQueryResponse(
            nodes=[GraphNode(**n) for n in result["nodes"]],
            edges=[GraphOverviewEdge(**e) for e in result["edges"]],
            raw_records=result["raw_records"],
            execution_time_ms=result["execution_time_ms"],
            record_count=result["record_count"],
        )
    )


@router.get("/health")
async def health_check():
    """
    Graph 服务健康检查
    """
    service = get_graph_service()
    healthy = service.health_check()

    if not healthy:
        raise HTTPException(status_code=503, detail="Graph service unavailable")

    return ApiResponse(data={"status": "healthy"})
