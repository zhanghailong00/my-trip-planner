"""基于 LangGraph 的旅行规划 Agent

LangGraph 是 LangChain 推出的一个用于构建有状态、多步骤 AI Agent 的框架。
它使用图 (Graph) 的方式来组织 Agent 的工作流程:

工作流程图:
┌─────────────┐
│  attraction  │ (1. 先搜索景点)
│   (景点)      │ 
└─────────────┘ 
       │
       ├────────────────┐
       ↓                ↓
┌─────────────┐  ┌─────────────┐
│   weather   │  │    hotel    │ (2. 并行获取天气和酒店)
│   (天气)      │  │    (住宿)    │ (注: 酒店会搜索景点周边)
└─────────────┘  └─────────────┘
       │                │
       └───────┬────────┘
               ↓
        ┌─────────────┐
        │   planner   │ (3. 最后整合生成规划)
        │   (规划)     │
        └───────┬─────┘
                ↓
              [END]

核心概念:
1. State (状态): 在节点间传递的数据容器，是一个 TypedDict
2. Node (节点): 执行特定任务的 Python 函数
3. Edge (边): 连接节点的线，定义执行流程
4. Graph (图): 由节点和边组成的完整工作流

每个节点是一个 Python 函数，签名如下:
    def node(state: State) -> Dict[str, Any]:
        # 处理逻辑
        return {"key": "value"}  # 返回要更新到 state 的数据

本模块实现了以下节点:
- attraction: 使用高德地图搜索目的地景点候选
- weather: 使用高德地图获取该城市天气预报
- hotel: 根据景点节点找到的位置，搜索周边的酒店候选
- planner: 使用 LLM 综合所有信息 (景点+天气+周边酒店) 生成最终旅行计划
"""

import json
import logging
import operator
import time
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from ..models.schemas import (
    Attraction,
    Budget,
    DayPlan,
    Hotel,
    Location,
    Meal,
    TripPlan,
    TripRequest,
    WeatherInfo,
)
from ..services.amap_service import get_amap_service
from ..services.llm_service import get_llm


# ============================================
# Agent System Prompt (结构化格式)
# ============================================

PLANNER_SYSTEM_PROMPT = """## 角色定义

你是一位专业的旅行规划专家，擅长根据用户需求生成详细的多日旅行行程。

## 核心任务

根据用户提供的目的地、日期、偏好等信息，结合候选景点、天气、酒店数据，生成一份完整的旅行计划。

## 必须遵守的约束

1. 严格按照指定的JSON格式返回，不要返回任何额外的解释文本
2. 天气温度必须是纯数字格式（如"28"），不能包含"°C"等符号
3. 每天安排2-3个景点，必须包含早、中、晚三餐
4. 每个景点必须包含真实的经纬度坐标（来自候选数据）
5. 预算估算要合理，符合实际消费水平
6. 每天的行程要符合逻辑，不要把相距很远的景点安排在同一天

## 输出格式（严格遵循）

```json
{
    "city": "城市名",
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "days": 数字,
    "weather_info": [
        {
            "date": "日期",
            "day_weather": "白天天气",
            "night_weather": "夜间天气",
            "day_temp": "温度数字",
            "night_temp": "夜间温度",
            "wind_direction": "风向",
            "wind_power": "风力"
        }
    ],
    "overall_suggestions": "整体旅行建议",
    "budget": {
        "total_attractions": 景点总费用,
        "total_hotels": 住宿总费用,
        "total_meals": 餐饮总费用,
        "total_transportation": 交通总费用,
        "total": 总费用
    },
    "days_plan": [
        {
            "date": "日期",
            "day_index": 0,
            "day_of_week": "星期几",
            "attractions": [
                {
                    "name": "景点名称",
                    "address": "地址",
                    "location": {"longitude": 经度, "latitude": 纬度},
                    "visit_duration": 游览时间(分钟),
                    "description": "景点描述",
                    "category": "景点类别",
                    "ticket_price": 门票价格
                }
            ],
            "meals": [
                {
                    "type": "breakfast/lunch/dinner/snack",
                    "name": "餐饮名称",
                    "address": "地址(可选)",
                    "description": "推荐菜/特色",
                    "estimated_cost": 预估费用
                }
            ],
            "hotel": {
                "name": "酒店名称",
                "address": "地址",
                "estimated_cost": 每晚费用
            },
            "summary": "当日行程摘要"
        }
    ]
}
```

## 禁止行为

- 禁止编造不存在的景点信息，必须使用候选数据中的景点
- 禁止返回非JSON格式的内容
- 禁止遗漏任何必须字段
- 禁止在温度字段中包含"°"符号
- 禁止安排同一天游览距离过远的景点

## Few-Shot示例

以下是一个合法的输出片段：

```json
{
    "city": "北京",
    "days_plan": [
        {
            "date": "2025-06-01",
            "day_index": 0,
            "day_of_week": "星期日",
            "attractions": [
                {
                    "name": "故宫博物院",
                    "address": "北京市东城区景山前街4号",
                    "location": {"longitude": 116.397428, "latitude": 39.90923},
                    "visit_duration": 180,
                    "description": "中国明清两代的皇家宫殿",
                    "category": "历史古迹",
                    "ticket_price": 60
                }
            ],
            "meals": [
                {"type": "breakfast", "name": "护国寺小吃", "description": "老北京特色早餐", "estimated_cost": 30},
                {"type": "lunch", "name": "全聚德烤鸭", "description": "北京烤鸭", "estimated_cost": 150},
                {"type": "dinner", "name": "东来顺涮肉", "description": "老北京涮羊肉", "estimated_cost": 120}
            ],
            "hotel": {
                "name": "如家酒店(故宫店)",
                "address": "北京市东城区南池子大街",
                "estimated_cost": 350
            },
            "summary": "上午参观故宫博物院，下午可在周边胡同漫步，晚上品尝北京特色美食"
        }
    ]
}
```"""


# ============================================
# 日志配置
# ============================================
logger = logging.getLogger(__name__)


# ============================================
# LangGraph State 定义
# ============================================

class TripPlannerState(TypedDict, total=False):
    """旅行规划 Agent 的状态

    这是一个 TypedDict，定义了在图执行过程中传递的状态数据。
    total=False 表示所有字段都是可选的。

    State 在整个图执行过程中在节点间传递，
    每个节点可以读取 state，也可以返回要更新的字段。

    使用 Annotated + operator.add 实现列表字段的追加语义，
    避免并行执行时数据覆盖问题。
    """
    request: TripRequest                                    # 用户请求
    attraction_candidates: Annotated[List[Dict], operator.add]  # 景点候选列表（追加）
    weather_candidates: Annotated[List[Dict], operator.add]     # 天气候选列表（追加）
    hotel_candidates: Annotated[List[Dict], operator.add]       # 酒店候选列表（追加）
    trip_plan: Optional[TripPlan]                           # 最终生成的旅行计划
    planner_error_messages: Annotated[List[str], operator.add]  # 重试错误信息（追加）
    planner_retry_count: int                                # 重试计数


# ============================================
# LangGraph 节点实现
# ============================================

class MultiAgentTripPlanner:
    """基于 LangGraph 的多 Agent 旅行规划系统
    
    使用 LangGraph 的 StateGraph 构建旅行规划工作流，
    通过并行执行多个节点 (景点/天气/酒店) 来提高效率，
    最后由 planner 节点整合所有信息生成最终计划。
    
    使用方式:
        planner = MultiAgentTripPlanner()
        result = planner.plan_trip(trip_request)
    """
    
    def __init__(self):
        """初始化旅行规划 Agent"""
        logger.info("[INIT] 初始化 LangGraph 旅行规划系统...")

        self.name = "langgraph-trip-planner"
        self.llm = get_llm()
        self.amap_service = get_amap_service()

        # 构建 LangGraph 工作流
        self.graph = self._build_graph()

        logger.info("[SUCCESS] LangGraph 旅行规划系统初始化完成")
    
    def _build_graph(self):
        """构建 LangGraph 工作流图
        
        定义节点和边，构建完整的工作流程:
        
        attraction ──┐
                    ├──→ planner → END
        weather   ──┤
                    │
        hotel     ──┘
        """
        # 创建状态图，指定状态类型
        workflow = StateGraph(TripPlannerState)
        
        # 注册节点
        workflow.add_node("attraction", self._attraction_node)
        workflow.add_node("weather", self._weather_node)
        workflow.add_node("hotel", self._hotel_node)
        workflow.add_node("planner", self._planner_node)
        
        # 设置入口点 (第一个执行的节点)
        workflow.set_entry_point("attraction")
        
        # 定义边 (节点之间的连接关系)
        # attraction 完成后，并行执行 weather 和 hotel
        workflow.add_edge("attraction", "weather")
        workflow.add_edge("attraction", "hotel")
        
        # weather 和 hotel 都完成后，才执行 planner
        workflow.add_edge("weather", "planner")
        workflow.add_edge("hotel", "planner")
        
        # planner 完成后，流程结束
        workflow.add_edge("planner", END)
        
        # 编译图，生成可执行的图对象
        return workflow.compile()
    
    def plan_trip(self, request: TripRequest) -> TripPlan:
        """执行旅行规划

        这是主入口方法，调用 LangGraph 执行完整的工作流程。

        Args:
            request: TripRequest 对象，包含用户的旅行需求

        Returns:
            TripPlan 对象，包含生成的完整旅行计划
        """
        start_time = time.time()
        logger.info("[START] 开始 LangGraph 旅行规划...")
        logger.info("   目的地: %s", request.city)
        logger.info("   日期: %s 至 %s", request.start_date, request.end_date)
        logger.info("   天数: %d天", request.travel_days)

        try:
            # 调用 graph.invoke() 执行工作流
            # 输入是初始状态，这里只传入 request
            final_state = self.graph.invoke({"request": request})

            # 从最终状态中获取生成的旅行计划
            trip_plan = final_state.get("trip_plan")

            if not trip_plan:
                # 如果生成失败，返回一个备用计划
                return self._create_fallback_plan(request)

            elapsed = time.time() - start_time
            logger.info("[SUCCESS] 旅行规划完成，总耗时: %.2f秒", elapsed)
            return trip_plan

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error("[ERROR] LangGraph 规划失败，耗时: %.2f秒, 错误: %s", elapsed, str(e))
            import traceback
            logger.debug(traceback.format_exc())
            return self._create_fallback_plan(request)
    
    # ============================================
    # 节点实现
    # ============================================
    
    def _attraction_node(self, state: TripPlannerState) -> Dict[str, Any]:
        """景点节点

        搜索用户指定城市的景点候选。
        这个节点会在图执行时第一个运行。

        Args:
            state: 当前状态，包含 request (用户请求)

        Returns:
            要更新到 state 的数据，必须是可以合并到 state 的字典
        """
        start_time = time.time()
        request = state["request"]

        # 根据用户偏好确定搜索关键词
        keywords = request.preferences[0] if request.preferences else "景点"

        logger.info("[SEARCH] 搜索景点: 关键词=%s, 城市=%s", keywords, request.city)

        # 调用高德地图搜索 POI
        pois = self.amap_service.search_poi(
            keywords=keywords,
            city=request.city,
            citylimit=True
        )

        # 如果没有结果，尝试通用搜索
        if not pois:
            pois = self.amap_service.search_poi(
                keywords="景点",
                city=request.city,
                citylimit=True
            )

        # 转换为候选数据格式
        candidates: List[Dict[str, Any]] = []
        for poi in pois[:12]:  # 最多取12个
            candidates.append({
                "name": poi.name,
                "address": poi.address,
                "location": {
                    "longitude": poi.location.longitude,
                    "latitude": poi.location.latitude,
                },
                "category": poi.type or "景点",
                "poi_id": poi.poi_id,
            })

        elapsed = time.time() - start_time
        logger.info("[SUCCESS] 景点搜索完成，候选数量: %d, 耗时: %.2f秒", len(candidates), elapsed)

        # 返回更新的状态数据
        return {"attraction_candidates": candidates}
    
    def _weather_node(self, state: TripPlannerState) -> Dict[str, Any]:
        """天气节点

        获取目的城市的天气预报。
        这个节点与 hotel 节点并行执行。

        Args:
            state: 当前状态

        Returns:
            天气候选数据
        """
        start_time = time.time()
        request = state["request"]

        logger.info("[WEATHER] 获取天气预报: 城市=%s", request.city)

        # 调用高德地图获取天气
        weather_list = self.amap_service.get_weather(request.city)

        # 转换为候选数据格式
        candidates: List[Dict[str, Any]] = []
        for w in weather_list:
            candidates.append({
                "date": w.date,
                "day_weather": w.day_weather,
                "night_weather": w.night_weather,
                "day_temp": w.day_temp,
                "night_temp": w.night_temp,
                "wind_direction": w.wind_direction,
                "wind_power": w.wind_power,
            })

        elapsed = time.time() - start_time
        logger.info("[SUCCESS] 天气预报获取完成，预报天数: %d, 耗时: %.2f秒", len(candidates), elapsed)

        return {"weather_candidates": candidates}
    
    def _hotel_node(self, state: TripPlannerState) -> Dict[str, Any]:
        """酒店节点

        搜索用户偏好类型的酒店候选。
        优化：优先根据景点节点找到的第一个景点位置搜索周边酒店。

        Args:
            state: 当前状态，包含 request 和 attraction_candidates

        Returns:
            酒店候选数据
        """
        start_time = time.time()
        request = state["request"]
        attractions = state.get("attraction_candidates", [])

        # 根据用户偏好确定搜索关键词
        hotel_keyword = request.accommodation if request.accommodation else "酒店"

        # 尝试获取第一个景点的坐标作为中心点
        center_location = None
        if attractions:
            first_attraction = attractions[0]
            loc_data = first_attraction.get("location", {})
            center_location = Location(
                longitude=loc_data.get("longitude", 0),
                latitude=loc_data.get("latitude", 0)
            )
            logger.info("[HOTEL] 正在搜索景点【%s】周边的酒店...", first_attraction['name'])
        else:
            logger.info("[HOTEL] 未找到景点，将在 %s 全城搜索酒店...", request.city)

        # 调用高德地图搜索酒店 (传入中心点坐标)
        pois = self.amap_service.search_poi(
            keywords=hotel_keyword,
            city=request.city,
            location=center_location,
            radius=5000,  # 5公里范围内
            citylimit=True
        )

        # 如果周边没有结果，尝试全城通用搜索
        if not pois:
            pois = self.amap_service.search_poi(
                keywords="酒店",
                city=request.city,
                citylimit=True
            )

        # 转换为候选数据格式
        candidates: List[Dict[str, Any]] = []
        for poi in pois[:8]:  # 最多取8个
            candidates.append({
                "name": poi.name,
                "address": poi.address,
                "location": {
                    "longitude": poi.location.longitude,
                    "latitude": poi.location.latitude,
                },
                "category": poi.type or "酒店",
            })

        elapsed = time.time() - start_time
        logger.info("[SUCCESS] 酒店搜索完成，候选数量: %d, 耗时: %.2f秒", len(candidates), elapsed)

        return {"hotel_candidates": candidates}
    
    def _planner_node(self, state: TripPlannerState) -> Dict[str, Any]:
        """规划节点 (核心节点)

        整合所有候选数据 (景点、天气、酒店)，
        使用 LLM 生成最终的旅行计划。

        这是整个工作流的汇聚点，weather 和 hotel 完成后都会汇聚到这里。

        Args:
            state: 当前状态，包含所有候选数据

        Returns:
            生成的 TripPlan
        """
        start_time = time.time()
        request = state["request"]
        attractions = state.get("attraction_candidates", [])
        weather_list = state.get("weather_candidates", [])
        hotels = state.get("hotel_candidates", [])

        logger.info("[PLAN] 开始生成旅行计划...")
        logger.info("   景点候选: %d 个", len(attractions))
        logger.info("   天气预报: %d 天", len(weather_list))
        logger.info("   酒店候选: %d 个", len(hotels))

        # 构建给 LLM 的提示词
        prompt = self._build_planning_prompt(
            request, attractions, weather_list, hotels
        )

        # 调用 LLM 生成计划
        response = self.llm.invoke(prompt)

        # 解析 LLM 返回的 JSON
        try:
            # 尝试提取 JSON
            plan_data = self._extract_json_from_response(response)

            if plan_data:
                # 转换为 TripPlan 对象
                trip_plan = self._build_trip_plan(plan_data, request)
                elapsed = time.time() - start_time
                logger.info("[SUCCESS] 旅行计划生成成功! 耗时: %.2f秒", elapsed)
                return {"trip_plan": trip_plan}
            else:
                logger.warning("[WARNING] LLM 返回格式错误，使用备用计划")
                return {"trip_plan": self._create_fallback_plan(request)}

        except Exception as e:
            logger.error("[ERROR] 解析旅行计划失败: %s", str(e))
            return {"trip_plan": self._create_fallback_plan(request)}
    
    # ============================================
    # 辅助方法
    # ============================================
    
    def _build_planning_prompt(
        self,
        request: TripRequest,
        attractions: List[Dict],
        weather_list: List[Dict],
        hotels: List[Dict]
    ) -> str:
        """构建给 LLM 的规划提示词
        
        将用户请求和候选数据组合成一个完整的提示词，
        包含所有必要信息让 LLM 生成合理的旅行计划。
        """
        # 组合景点信息
        attraction_text = "\n".join([
            f"- {a['name']} (分类:{a.get('category','景点')}): 地址{a['address']}, "
            f"坐标({a['location']['longitude']},{a['location']['latitude']})"
            for a in attractions
        ])
        
        # 组合天气信息
        weather_text = "\n".join([
            f"- {w['date']}: {w['day_weather']}/{w['night_weather']}, "
            f"温度{w['day_temp']}°C/{w['night_temp']}°C, {w['wind_direction']}{w['wind_power']}"
            for w in weather_list
        ])
        
        # 组合酒店信息
        hotel_text = "\n".join([
            f"- {h['name']}: 地址{h['address']}"
            for h in hotels
        ])
        
        # 组合用户偏好
        preference_text = ", ".join(request.preferences) if request.preferences else "无"
        
        # 构建完整提示词
        prompt = f"""{PLANNER_SYSTEM_PROMPT}

## 用户需求
- 目的地: {request.city}
- 旅行日期: {request.start_date} 至 {request.end_date} (共{request.travel_days}天)
- 交通方式: {request.transportation}
- 住宿偏好: {request.accommodation}
- 用户偏好: {preference_text}
- 额外要求: {request.free_text_input or "无"}

## 景点候选 (请从中选择{request.travel_days * 2}-{request.travel_days * 3}个)
{attraction_text}

## 天气预报
{weather_text}

## 酒店候选 (请选择合适的住宿)
{hotel_text}

请严格按照JSON格式返回旅行计划。
"""
        return prompt
    
    @staticmethod
    def _extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
        """从 LLM 响应中提取 JSON 数据
        
        支持多种格式:
        1. 纯 JSON
        2. Markdown 代码块包裹的 JSON
        3. 文本中的 JSON 片段
        """
        import re
        
        response = response.strip()
        
        # 方法1: 尝试直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # 方法2: 提取 Markdown 代码块
        code_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
        if code_match:
            try:
                return json.loads(code_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 方法3: 提取 JSON 对象
        brace_match = re.search(r"\{.*\}", response, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _build_trip_plan(
        self,
        plan_data: Dict[str, Any],
        request: TripRequest
    ) -> TripPlan:
        """将 LLM 返回的 JSON 数据转换为 TripPlan 对象
        
        进行数据验证和类型转换，确保符合 Pydantic 模型定义。
        """
        # 构建天气信息
        weather_info = []
        for w in plan_data.get("weather_info", []):
            weather_info.append(WeatherInfo(
                date=w.get("date", ""),
                day_weather=w.get("day_weather", ""),
                night_weather=w.get("night_weather", ""),
                day_temp=str(w.get("day_temp", "0")),
                night_temp=str(w.get("night_temp", "0")),
                wind_direction=w.get("wind_direction", ""),
                wind_power=w.get("wind_power", "")
            ))
        
        # 构建每日计划
        days_plan = []
        for day_data in plan_data.get("days_plan", []):
            # 构建景点列表
            attractions = []
            for a in day_data.get("attractions", []):
                loc = a.get("location", {})
                attractions.append(Attraction(
                    name=a.get("name", ""),
                    address=a.get("address", ""),
                    location=Location(
                        longitude=loc.get("longitude", 0),
                        latitude=loc.get("latitude", 0)
                    ),
                    visit_duration=a.get("visit_duration", 120),
                    description=a.get("description", ""),
                    category=a.get("category", "景点"),
                    ticket_price=a.get("ticket_price", 0)
                ))
            
            # 构建餐饮列表
            meals = []
            for m in day_data.get("meals", []):
                meals.append(Meal(
                    type=m.get("type", "lunch"),
                    name=m.get("name", ""),
                    address=m.get("address"),
                    description=m.get("description"),
                    estimated_cost=m.get("estimated_cost", 0)
                ))
            
            # 构建酒店 (如果有)
            hotel = None
            if day_data.get("hotel"):
                h = day_data["hotel"]
                hotel = Hotel(
                    name=h.get("name", ""),
                    address=h.get("address", ""),
                    estimated_cost=h.get("estimated_cost", 0)
                )
            
            # 构建单日计划
            day_plan = DayPlan(
                date=day_data.get("date", ""),
                day_index=day_data.get("day_index", 0),
                day_of_week=day_data.get("day_of_week", ""),
                attractions=attractions,
                meals=meals,
                hotel=hotel,
                summary=day_data.get("summary", ""),
                weather=weather_info[day_data.get("day_index", 0)] if day_data.get("day_index", 0) < len(weather_info) else None
            )
            days_plan.append(day_plan)
        
        # 构建预算
        budget_data = plan_data.get("budget", {})
        budget = Budget(
            total_attractions=budget_data.get("total_attractions", 0),
            total_hotels=budget_data.get("total_hotels", 0),
            total_meals=budget_data.get("total_meals", 0),
            total_transportation=budget_data.get("total_transportation", 0),
            total=budget_data.get("total", 0)
        )
        
        # 构建完整计划
        return TripPlan(
            city=plan_data.get("city", request.city),
            start_date=plan_data.get("start_date", request.start_date),
            end_date=plan_data.get("end_date", request.end_date),
            days=plan_data.get("days", request.travel_days),
            days_plan=days_plan,
            weather_info=weather_info,
            overall_suggestions=plan_data.get("overall_suggestions", ""),
            budget=budget,
            created_at=datetime.now().isoformat()
        )
    
    def _create_fallback_plan(self, request: TripRequest) -> TripPlan:
        """创建备用旅行计划

        当 LLM 生成失败时，使用硬编码的示例计划作为后备
        """
        logger.warning("[WARNING] 使用备用计划模板")
        
        # 生成日期列表
        start = datetime.strptime(request.start_date, "%Y-%m-%d")
        days_plan = []
        weather_info = []
        
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        
        for i in range(request.travel_days):
            current_date = start.replace(day=start.day + i)
            date_str = current_date.strftime("%Y-%m-%d")
            weekday = weekdays[current_date.weekday()]
            
            days_plan.append(DayPlan(
                date=date_str,
                day_index=i,
                day_of_week=weekday,
                attractions=[
                    Attraction(
                        name=f"{request.city}经典景点{i+1}",
                        address=f"{request.city}市中心",
                        location=Location(longitude=116.397428, latitude=39.90923),
                        visit_duration=120,
                        description="推荐游览",
                        category="景点"
                    )
                ],
                meals=[
                    Meal(type="breakfast", name="当地早餐", estimated_cost=30),
                    Meal(type="lunch", name="特色午餐", estimated_cost=80),
                    Meal(type="dinner", name="美食晚餐", estimated_cost=100)
                ],
                summary=f"第{i+1}天: 探索{request.city}"
            ))
            
            weather_info.append(WeatherInfo(
                date=date_str,
                day_weather="晴",
                night_weather="多云",
                day_temp="25",
                night_temp="18",
                wind_direction="东南风",
                wind_power="2级"
            ))
        
        return TripPlan(
            city=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            days=request.travel_days,
            days_plan=days_plan,
            weather_info=weather_info,
            overall_suggestions="请查看具体行程安排，注意天气变化。",
            budget=Budget(total=500),
            created_at=datetime.now().isoformat()
        )
    
    def get_runtime_info(self) -> Dict[str, Any]:
        """获取 Agent 运行时信息
        
        用于健康检查和监控
        """
        return {
            "name": self.name,
            "framework": "langgraph",
            "nodes": ["attraction", "weather", "hotel", "planner"],
            "status": "running"
        }
