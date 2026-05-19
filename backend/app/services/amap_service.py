"""高德地图服务封装

支持两种调用方式:
1. MCP模式 (amap-mcp-server): 通过 MCP 协议调用
2. Direct模式 (直接HTTP): 直接调用高德地图 Web API

默认使用 Direct 模式，因为 amap-mcp-server 在 Windows 上存在兼容性问题
"""

import logging
from typing import Any, Dict, List, Optional

from ..config import get_settings
from ..models.schemas import Location, POIInfo, WeatherInfo

logger = logging.getLogger(__name__)

# 尝试导入 MCP 客户端 (如果需要使用 MCP 模式)
try:
    from .mcp_client import StdioMCPClient
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


class AmapService:
    """高德地图服务封装类

    支持 MCP 和直接 HTTP 两种调用方式:
    - MCP: 通过 amap-mcp-server (需要配置 AMAP_PROVIDER=mcp)
    - Direct: 直接调用 Web API (默认，推荐)

    Attributes:
        api_key: 高德地图 API Key
        provider: 当前使用的调用方式
        capabilities: 支持的功能列表
    """

    def __init__(self):
        """初始化高德地图服务"""
        settings = get_settings()

        if not settings.amap_api_key:
            raise ValueError(
                "高德地图API Key未配置，请在.env文件中设置 AMAP_API_KEY\n"
                "申请地址: https://console.amap.com/dev/key/app"
            )

        self.api_key = settings.amap_api_key
        self.provider = settings.amap_provider
        self.capabilities = [
            "poi_search",
            "weather",
            "route_plan",
            "geocode",
            "poi_detail",
        ]

        # 根据配置选择调用方式
        if self.provider == "mcp" and MCP_AVAILABLE:
            self._use_mcp()
        else:
            self._use_direct()

    def _use_mcp(self) -> None:
        """使用 MCP 方式调用高德地图服务"""
        import os
        from .mcp_client import StdioMCPClient

        settings = get_settings()
        cmd = settings.get_amap_mcp_command_list()
        env = {"AMAP_MAPS_API_KEY": self.api_key}

        self._mcp_client = StdioMCPClient(
            command=cmd,
            env=env,
            timeout=settings.amap_mcp_timeout,
        )
        self._mcp_client.start()
        self._tools_cache = self._mcp_client.list_tools()
        logger.info("[SUCCESS] 高德地图服务初始化成功 (MCP), 工具数量: %d", len(self._tools_cache))

    def _use_direct(self) -> None:
        """使用直接 HTTP 方式调用高德地图服务"""
        from . import amap_direct_service as direct

        self._direct_service = direct.get_amap_direct_service()
        logger.info("[SUCCESS] 高德地图服务初始化成功 (直接HTTP调用)")

    # ============================================
    # 公开 API
    # ============================================

    def search_poi(
        self,
        keywords: str,
        city: str,
        location: Optional[Location] = None,
        radius: int = 5000,
        citylimit: bool = True,
        offset: int = 20,
        page: int = 1
    ) -> List[POIInfo]:
        """搜索 POI 兴趣点

        Args:
            keywords: 搜索关键词，如 "景点"、"酒店"、"餐厅"
            city: 搜索所在城市
            location: 中心点坐标 (用于周边搜索,暂不支持)
            radius: 搜索半径 (米)，默认 5000
            citylimit: 是否限制在城市范围内
            offset: 每页数量，默认20
            page: 页码，默认1

        Returns:
            POIInfo 对象列表
        """
        if hasattr(self, '_direct_service'):
            # 直接 HTTP 模式
            return self._direct_service.search_poi(
                keywords=keywords,
                city=city,
                citylimit=citylimit,
                offset=offset,
                page=page
            )
        else:
            # MCP 模式
            return self._search_poi_mcp(keywords, city, citylimit, offset, page)

    def _search_poi_mcp(
        self,
        keywords: str,
        city: str,
        citylimit: bool,
        offset: int,
        page: int
    ) -> List[POIInfo]:
        """MCP 模式: 搜索 POI"""
        result = self._call_tool("poi_search", {
            "keywords": keywords,
            "city": city,
            "citylimit": citylimit,
            "offset": offset,
            "page": page
        })

        text = self._extract_text_from_result(result)
        pois = self._parse_poi_from_text(text)
        logger.info("[POI] POI搜索完成: 关键词=%s, 城市=%s, 结果数=%d", keywords, city, len(pois))
        return pois

    def get_weather(self, city: str) -> List[WeatherInfo]:
        """获取城市天气预报

        Args:
            city: 城市名称

        Returns:
            WeatherInfo 对象列表 (包含3-4天预报)
        """
        if hasattr(self, '_direct_service'):
            # 直接 HTTP 模式
            return self._direct_service.get_weather(city)
        else:
            # MCP 模式
            return self._get_weather_mcp(city)

    def _get_weather_mcp(self, city: str) -> List[WeatherInfo]:
        """MCP 模式: 获取天气"""
        result = self._call_tool("weather", {"city": city})

        text = self._extract_text_from_result(result)
        data = self._extract_json_from_text(text)

        weather_list: List[WeatherInfo] = []
        lives = data.get("lives", data.get("forecasts", []))

        if isinstance(lives, list):
            for w in lives:
                weather_list.append(WeatherInfo(
                    date=w.get("date", ""),
                    day_weather=w.get("day_weather", ""),
                    night_weather=w.get("night_weather", w.get("weather", "")),
                    day_temp=str(w.get("day_temp", w.get("temperature", "0"))),
                    night_temp=str(w.get("night_temp", "0")),
                    wind_direction=w.get("wind_direction", ""),
                    wind_power=w.get("wind_power", "")
                ))

        logger.info("[WEATHER] 天气查询完成: 城市=%s, 预报天数=%d", city, len(weather_list))
        return weather_list

    def get_poi_detail(self, poi_id: str) -> Optional[POIInfo]:
        """获取 POI 详细信息"""
        if hasattr(self, '_direct_service'):
            return None
        else:
            return self._get_poi_detail_mcp(poi_id)

    def _get_poi_detail_mcp(self, poi_id: str) -> Optional[POIInfo]:
        """MCP 模式: 获取 POI 详情"""
        result = self._call_tool("poi_detail", {"id": poi_id})
        text = self._extract_text_from_result(result)
        data = self._extract_json_from_text(text)
        poi_data = data.get("poi", data)
        if poi_data:
            return self._normalize_poi_item(poi_data)
        return None

    def geocode(self, address: str, city: str = "") -> Optional[Location]:
        """地址编码: 将地址转换为坐标"""
        if hasattr(self, '_direct_service'):
            return self._direct_service.geocode(address, city)
        else:
            return self._geocode_mcp(address, city)

    def _geocode_mcp(self, address: str, city: str = "") -> Optional[Location]:
        """MCP 模式: 地理编码"""
        params = {"address": address}
        if city:
            params["city"] = city

        result = self._call_tool("geocode", params)
        text = self._extract_text_from_result(result)
        data = self._extract_json_from_text(text)
        location_str = data.get("location", "")
        return self._normalize_location(location_str)

    def regeocode(self, longitude: float, latitude: float) -> Optional[str]:
        """逆地理编码: 将坐标转换为地址"""
        if hasattr(self, '_direct_service'):
            return self._direct_service.regeocode(longitude, latitude)
        else:
            return self._regeocode_mcp(longitude, latitude)

    def _regeocode_mcp(self, longitude: float, latitude: float) -> Optional[str]:
        """MCP 模式: 逆地理编码"""
        result = self._call_tool("regeocode", {
            "longitude": longitude,
            "latitude": latitude
        })
        text = self._extract_text_from_result(result)
        data = self._extract_json_from_text(text)
        return data.get("formatted_address", "")

    def stop(self) -> None:
        """停止高德地图 MCP 服务"""
        if hasattr(self, '_mcp_client') and self._mcp_client:
            self._mcp_client.stop()
            self._mcp_client = None

    # ============================================
    # MCP 模式辅助方法
    # ============================================

    def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用指定的 MCP 工具"""
        if not hasattr(self, '_mcp_client') or not self._mcp_client:
            raise RuntimeError("MCP客户端未初始化")

        try:
            return self._mcp_client.call_tool(tool_name, arguments)
        except Exception as e:
            logger.warning("[WARNING] 调用高德地图工具 %s 失败: %s", tool_name, str(e))
            raise

    @staticmethod
    def _extract_text_from_result(result: Dict[str, Any]) -> str:
        """从 MCP 工具结果中提取文本内容"""
        content = result.get("content", [])
        texts: List[str] = []

        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(str(item.get("text", "")))

        return "\n".join(texts) if texts else ""

    @staticmethod
    def _extract_json_from_text(text: str) -> Dict[str, Any]:
        """从文本中提取 JSON 数据"""
        import json
        import re

        text = text.strip()
        if not text:
            return {}

        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        code_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if code_match:
            try:
                return json.loads(code_match.group(1))
            except json.JSONDecodeError:
                pass

        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        return {}

    def _normalize_location(self, location_str: str) -> Optional[Location]:
        """将位置字符串转换为 Location 对象"""
        if not location_str:
            return None

        try:
            if isinstance(location_str, str) and "," in location_str:
                parts = location_str.split(",")
                return Location(
                    longitude=float(parts[0]),
                    latitude=float(parts[1])
                )

            if isinstance(location_str, dict):
                return Location(
                    longitude=float(location_str.get("lng", 0)),
                    latitude=float(location_str.get("lat", 0))
                )
        except (ValueError, TypeError):
            pass

        return None

    def _normalize_poi_item(self, poi: Dict[str, Any]) -> Optional[POIInfo]:
        """将原始 POI 数据规范化为 POIInfo 对象"""
        try:
            location = self._normalize_location(poi.get("location", ""))
            if location is None:
                return None

            return POIInfo(
                poi_id=str(poi.get("id", "")),
                name=poi.get("name", ""),
                address=poi.get("address", ""),
                location=location,
                type=poi.get("type", ""),
                phone=poi.get("tel", ""),
                rating=None
            )
        except Exception:
            return None

    def _parse_poi_from_text(self, text: str) -> List[POIInfo]:
        """从文本中解析 POI 列表"""
        pois: List[POIInfo] = []

        data = self._extract_json_from_text(text)
        poi_list = data.get("pois", [])

        if not poi_list and "pois" in text:
            import json
            try:
                import re
                match = re.search(r'"pois"\s*:\s*\[(.*?)\]', text, re.DOTALL)
                if match:
                    poi_list = json.loads(f"[{match.group(1)}]")
            except:
                pass

        if isinstance(poi_list, list):
            for poi in poi_list:
                normalized = self._normalize_poi_item(poi)
                if normalized:
                    pois.append(normalized)

        return pois


# ============================================
# 服务单例
# ============================================

_amap_service: Optional[AmapService] = None


def get_amap_service() -> AmapService:
    """获取全局高德地图服务单例"""
    global _amap_service
    if _amap_service is None:
        _amap_service = AmapService()
    return _amap_service
