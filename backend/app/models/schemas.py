"""数据模型定义模块

使用 Pydantic 定义请求/响应的数据结构，提供自动验证和序列化功能

主要模型分类:
- 请求模型: TripRequest (旅行规划请求)
- 响应模型: TripPlan, DayPlan, Attraction, Meal, Hotel (旅行计划相关)
- 基础模型: Location, POIInfo, WeatherInfo (通用数据结构)
"""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


# ============================================
# 基础数据结构
# ============================================

class Location(BaseModel):
    """地理位置坐标
    
    用于表示POI、景点、酒店等的经纬度位置
    """
    longitude: float = Field(..., description="经度", example=116.397428)
    latitude: float = Field(..., description="纬度", example=39.90923)


class WeatherInfo(BaseModel):
    """天气信息
    
    包含日期、天气状况、温度、风力风向等信息
    """
    date: str = Field(..., description="日期 YYYY-MM-DD格式", example="2025-06-01")
    day_weather: str = Field(..., description="白天天气", example="晴")
    night_weather: str = Field(..., description="夜间天气", example="多云")
    day_temp: str = Field(..., description="白天温度", example="28")
    night_temp: str = Field(..., description="夜间温度", example="18")
    wind_direction: str = Field(..., description="风向", example="东南风")
    wind_power: str = Field(..., description="风力", example="3级")


class POIInfo(BaseModel):
    """POI (Point of Interest) 兴趣点信息
    
    从高德地图搜索返回的地点基本信息
    """
    poi_id: str = Field(default="", description="POI唯一标识ID")
    name: str = Field(..., description="地点名称", example="故宫博物院")
    address: str = Field(default="", description="详细地址")
    location: Location = Field(default=..., description="经纬度坐标")
    type: str = Field(default="", description="地点类型/分类")
    phone: str = Field(default="", description="联系电话")
    rating: Optional[float] = Field(default=None, description="评分(如果有)")


# ============================================
# 旅行请求模型
# ============================================

class TripRequest(BaseModel):
    """旅行规划请求

    用户提交的旅行需求，包含目的地、时间、交通住宿偏好等
    """
    thread_id: Optional[str] = Field(
        default=None,
        description="会话ID，用于checkpoint状态持久化",
        example="abc123-def456"
    )
    city: str = Field(..., description="目的地城市", example="北京")
    start_date: str = Field(..., description="开始日期 YYYY-MM-DD格式", example="2025-06-01")
    end_date: str = Field(..., description="结束日期 YYYY-MM-DD格式", example="2025-06-03")
    travel_days: int = Field(..., description="旅行天数", ge=1, le=30, example=3)
    transportation: str = Field(..., description="交通方式偏好", example="公共交通")
    accommodation: str = Field(..., description="住宿偏好/酒店类型", example="经济型酒店")
    preferences: List[str] = Field(
        default_factory=list,
        description="旅行偏好标签列表",
        example=["历史文化", "美食", "自然风光"]
    )
    free_text_input: Optional[str] = Field(
        default="",
        description="用户自由输入的额外要求",
        example="希望多安排一些博物馆"
    )


# ============================================
# 旅行计划组成模型
# ============================================

class Attraction(BaseModel):
    """景点/ attractions 信息
    
    行程中安排的具体景点，包含游览时间、门票等信息
    """
    name: str = Field(..., description="景点名称", example="故宫博物院")
    address: str = Field(..., description="景点地址")
    location: Location = Field(..., description="经纬度坐标")
    visit_duration: int = Field(..., description="建议游览时间(分钟)", example=120)
    description: str = Field(..., description="景点简介")
    category: str = Field(default="景点", description="景点类别", example="历史博物馆")
    rating: Optional[float] = Field(default=None, description="评分")
    ticket_price: int = Field(default=0, description="门票价格(元)")
    image_url: Optional[str] = Field(default=None, description="景点图片URL")
    poi_id: str = Field(default="", description="高德地图POI ID")


class Meal(BaseModel):
    """餐饮信息
    
    行程中安排的餐饮，包含早餐/午餐/晚餐/小吃类型
    """
    type: str = Field(..., description="餐饮类型: breakfast/lunch/dinner/snack", example="lunch")
    name: str = Field(..., description="餐厅/餐饮名称", example="全聚德烤鸭店")
    address: Optional[str] = Field(default=None, description="餐厅地址")
    location: Optional[Location] = Field(default=None, description="餐厅坐标")
    description: Optional[str] = Field(default=None, description="餐饮描述/推荐菜")
    estimated_cost: int = Field(default=0, description="预估费用(元)")


class Hotel(BaseModel):
    """酒店住宿信息
    
    行程中的住宿安排
    """
    name: str = Field(..., description="酒店名称", example="如家酒店")
    address: str = Field(default="", description="酒店地址")
    location: Optional[Location] = Field(default=None, description="酒店坐标")
    price_range: str = Field(default="", description="价格范围", example="200-300元/晚")
    rating: str = Field(default="", description="酒店评分", example="4.5分")
    distance: str = Field(default="", description="距离市中心/景点距离")
    estimated_cost: int = Field(default=0, description="预估费用(元/晚)")


class DayPlan(BaseModel):
    """单日行程计划
    
    包含一天的日期、星期、景点安排、餐饮安排等信息
    """
    date: str = Field(..., description="日期 YYYY-MM-DD格式")
    day_index: int = Field(..., description="第几天(从0开始)", example=0)
    day_of_week: str = Field(..., description="星期几", example="星期六")
    weather: Optional[WeatherInfo] = Field(default=None, description="当天天气预报")
    attractions: List[Attraction] = Field(default_factory=list, description="当天景点列表")
    meals: List[Meal] = Field(default_factory=list, description="当天餐饮安排")
    hotel: Optional[Hotel] = Field(default=None, description="当天住宿(仅住店日需要)")
    summary: str = Field(default="", description="当日行程摘要")


class Budget(BaseModel):
    """预算明细
    
    整个行程的预算分解
    """
    total_attractions: int = Field(default=0, description="景点门票总费用(元)")
    total_hotels: int = Field(default=0, description="住宿总费用(元)")
    total_meals: int = Field(default=0, description="餐饮总费用(元)")
    total_transportation: int = Field(default=0, description="交通总费用(元)")
    total: int = Field(default=0, description="预算总计(元)")


class TripPlan(BaseModel):
    """完整旅行计划
    
    包含整个行程的所有信息，是旅行规划的最终输出
    """
    city: str = Field(..., description="目的地城市")
    start_date: str = Field(..., description="开始日期")
    end_date: str = Field(..., description="结束日期")
    days: int = Field(..., description="旅行天数")
    days_plan: List[DayPlan] = Field(default_factory=list, description="每日行程列表")
    weather_info: List[WeatherInfo] = Field(default_factory=list, description="全程天气预报")
    overall_suggestions: str = Field(default="", description="整体旅行建议")
    budget: Budget = Field(default=Budget(), description="预算明细")
    created_at: str = Field(default="", description="计划生成时间")
