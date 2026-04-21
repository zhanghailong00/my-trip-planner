"""旅行规划 API 路由

提供旅行规划相关 API:
- POST /api/trip/plan: 生成旅行计划
"""

from fastapi import APIRouter, HTTPException

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


@router.post("/plan", response_model=TripPlan, summary="生成旅行计划")
async def create_trip_plan(request: TripRequest) -> TripPlan:
    """生成旅行计划
    
    接收用户的旅行需求，调用 LangGraph Agent 生成完整的旅行计划。
    
    Args:
        request: TripRequest 对象，包含目的地、日期、交通住宿偏好等
        
    Returns:
        TripPlan 对象，包含每日的景点、餐饮、住宿安排和预算
        
    Raises:
        HTTPException: 当生成失败时返回 500 错误
        
    Example:
        POST /api/trip/plan
        {
            "city": "北京",
            "start_date": "2025-06-01",
            "end_date": "2025-06-03",
            "travel_days": 3,
            "transportation": "公共交通",
            "accommodation": "经济型酒店",
            "preferences": ["历史文化", "美食"],
            "free_text_input": "希望多安排博物馆"
        }
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
