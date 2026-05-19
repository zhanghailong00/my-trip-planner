"""旅行规划 API 路由

提供旅行规划相关 API:
- POST /api/trip/plan: 生成旅行计划（完整流程）
- POST /api/trip/plan/start: 开始规划（到人工审核点暂停）
- POST /api/trip/resume/{thread_id}: 从审核点恢复
"""

from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...agents.trip_planner_agent import MultiAgentTripPlanner
from ...models.schemas import TripPlan, TripRequest

router = APIRouter(prefix="/trip", tags=["旅行规划"])

# 全局 Agent 实例 (延迟加载)
_trip_planner: MultiAgentTripPlanner | None = None


def get_trip_planner() -> MultiAgentTripPlanner:
    """获取旅行规划 Agent 实例 (延迟加载)"""
    global _trip_planner
    if _trip_planner is None:
        _trip_planner = MultiAgentTripPlanner()
    return _trip_planner


class PlanStartResponse(BaseModel):
    """开始规划响应"""
    thread_id: str
    attraction_candidates: List[Dict]
    weather_candidates: List[Dict]
    hotel_candidates: List[Dict]


@router.post("/plan", response_model=TripPlan, summary="生成旅行计划")
async def create_trip_plan(request: TripRequest) -> TripPlan:
    """生成旅行计划

    接收用户的旅行需求，调用 LangGraph Agent 生成完整的旅行计划。
    注意：由于 Human-in-the-loop 机制，此接口会暂停在审核点。

    Args:
        request: TripRequest 对象，包含目的地、日期、交通住宿偏好等

    Returns:
        TripPlan 对象，包含每日的景点、餐饮、住宿安排和预算

    Raises:
        HTTPException: 当生成失败时返回 500 错误
    """
    try:
        planner = get_trip_planner()
        trip_plan = planner.plan_trip(request)
        return trip_plan
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"生成旅行计划失败: {str(e)}"
        )


@router.post("/plan/start", response_model=PlanStartResponse, summary="开始旅行规划")
async def start_trip_plan(request: TripRequest) -> PlanStartResponse:
    """开始旅行规划（到人工审核点暂停）

    执行工作流直到审核点暂停，返回候选数据供用户审核。
    用户确认后，调用 /resume/{thread_id} 继续执行。

    Args:
        request: TripRequest 对象，包含目的地、日期、交通住宿偏好等

    Returns:
        PlanStartResponse 对象，包含 thread_id 和候选数据

    Raises:
        HTTPException: 当执行失败时返回 500 错误
    """
    try:
        planner = get_trip_planner()
        result = planner.start_plan_trip(request)
        return PlanStartResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"开始旅行规划失败: {str(e)}"
        )


@router.post("/resume/{thread_id}", response_model=TripPlan, summary="恢复旅行规划")
async def resume_trip_plan(thread_id: str) -> TripPlan:
    """恢复旅行规划（从审核点继续）

    从审核点继续执行，完成旅行计划生成。

    Args:
        thread_id: 会话ID，用于恢复 checkpoint 状态

    Returns:
        TripPlan 对象，包含生成的完整旅行计划

    Raises:
        HTTPException: 当恢复失败时返回 500 错误
    """
    try:
        planner = get_trip_planner()
        trip_plan = planner.resume_plan_trip(thread_id)
        if trip_plan is None:
            raise HTTPException(
                status_code=404,
                detail=f"未找到 Thread ID: {thread_id} 的会话状态"
            )
        return trip_plan
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"恢复旅行规划失败: {str(e)}"
        )
