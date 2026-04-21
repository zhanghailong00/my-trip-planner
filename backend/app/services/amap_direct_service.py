"""高德地图 Web API 服务封装 (直接HTTP调用)

绕过 MCP 协议，直接使用高德地图 Web 服务 API

API 文档: https://lbs.amap.com/api/webservice/guide/api

提供功能:
- POI 搜索: https://restapi.amap.com/v3/place/text
- 天气查询: https://restapi.amap.com/v3/weather/weatherInfo
- 地理编码: https://restapi.amap.com/v3/geocode/geocode
"""

import hashlib
import requests
from typing import Any, Dict, List, Optional

from ..config import get_settings
from ..models.schemas import Location, POIInfo, WeatherInfo


class AmapDirectService:
    """高德地图 Web API 服务封装类
    
    直接使用 HTTP 请求调用高德地图 Web 服务 API，不依赖 MCP 协议
    
    Attributes:
        api_key: 高德地图 API Key
        security_code: 高德地图安全密钥 (用于签名)
    """
    
    def __init__(self):
        """初始化高德地图服务
        
        Raises:
            ValueError: 当 API Key 未配置时
        """
        settings = get_settings()
        
        if not settings.amap_api_key:
            raise ValueError(
                "高德地图API Key未配置，请在.env文件中设置 AMAP_API_KEY\n"
                "申请地址: https://console.amap.com/dev/key/app"
            )
        
        self.api_key = settings.amap_api_key
        self.security_code = settings.amap_security_code
        self.base_url = "https://restapi.amap.com/v3"
        
        print(f"[SUCCESS] 高德地图服务初始化成功 (直接HTTP调用)")
    
    def _sign_params(self, params: Dict[str, Any]) -> str:
        """对请求参数进行签名
        
        高德地图 Web API 支持使用安全密钥进行签名验证
        
        Args:
            params: 原始参数字典
            
        Returns:
            签名后的参数字典
        """
        if not self.security_code:
            return params
        
        # 按key排序
        sorted_keys = sorted(params.keys())
        sign_str = ""
        for key in sorted_keys:
            sign_str += f"{key}{params[key]}"
        sign_str += self.security_code
        
        # MD5签名
        md5 = hashlib.md5(sign_str.encode('utf-8'))
        params['sig'] = md5.hexdigest()
        
        return params
    
    def _get(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """发送 GET 请求到高德地图 API
        
        Args:
            endpoint: API 端点路径
            params: 查询参数
            
        Returns:
            API 响应的 JSON 数据
        """
        url = f"{self.base_url}/{endpoint}"
        params['key'] = self.api_key
        
        # 添加签名 (如果有)
        if self.security_code:
            params = self._sign_params(params)
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # 检查 API 返回状态
        if data.get('status') != '1':
            error_info = data.get('info', '未知错误')
            raise RuntimeError(f"高德地图API错误: {error_info}, 详情: {data.get('info_desc', '')}")
        
        return data
    
    def search_poi(
        self,
        keywords: str,
        city: str,
        citylimit: bool = True,
        offset: int = 20,
        page: int = 1
    ) -> List[POIInfo]:
        """搜索 POI 兴趣点
        
        API: https://restapi.amap.com/v3/place/text
        
        Args:
            keywords: 搜索关键词
            city: 搜索所在城市
            citylimit: 是否限制在城市范围内
            offset: 每页数量
            page: 页码
            
        Returns:
            POIInfo 对象列表
        """
        params = {
            'keywords': keywords,
            'city': city,
            'citylimit': 'true' if citylimit else 'false',
            'offset': offset,
            'page': page,
            'types': '',  # 可指定类型筛选
        }
        
        data = self._get('place/text', params)
        
        pois: List[POIInfo] = []
        poi_list = data.get('pois', [])
        
        if not poi_list:
            print(f"[POI] POI搜索完成: 关键词={keywords}, 城市={city}, 结果数=0")
            return pois
        
        for poi_data in poi_list:
            try:
                location_str = poi_data.get('location', '')
                if not location_str or ',' not in location_str:
                    continue
                
                lng, lat = location_str.split(',')
                
                pois.append(POIInfo(
                    poi_id=poi_data.get('id', ''),
                    name=poi_data.get('name', ''),
                    address=poi_data.get('address', ''),
                    location=Location(
                        longitude=float(lng),
                        latitude=float(lat)
                    ),
                    type=poi_data.get('type', ''),
                    phone=poi_data.get('tel', '') or '',  # 确保是字符串
                ))
            except (ValueError, TypeError) as e:
                print(f"[WARNING] 解析POI失败: {poi_data.get('name', 'unknown')}, 错误: {e}")
                continue
        
        print(f"[POI] POI搜索完成: 关键词={keywords}, 城市={city}, 结果数={len(pois)}")
        return pois
    
    def get_weather(self, city: str) -> List[WeatherInfo]:
        """获取城市天气预报
        
        API: https://restapi.amap.com/v3/weather/weatherInfo
        
        Args:
            city: 城市名称
            
        Returns:
            WeatherInfo 对象列表
        """
        params = {
            'city': city,
            'extensions': 'all',  # 获取全部天气信息(实时+预报)
        }
        
        data = self._get('weather/weatherInfo', params)
        
        weather_list: List[WeatherInfo] = []
        
        # 尝试获取实时天气
        live = data.get('lives', [])
        for w in live:
            weather_list.append(WeatherInfo(
                date=w.get('reporttime', '')[:10],
                day_weather=w.get('weather', ''),
                night_weather=w.get('weather', ''),
                day_temp=w.get('temperature', '0'),
                night_temp=w.get('temperature', '0'),
                wind_direction=w.get('winddirection', ''),
                wind_power=w.get('windpower', '')
            ))
        
        # 尝试获取预报天气
        forecasts = data.get('forecasts', [])
        if forecasts:
            for fc in forecasts:
                for day in fc.get('casts', []):
                    weather_list.append(WeatherInfo(
                        date=day.get('date', ''),
                        day_weather=day.get('dayweather', ''),
                        night_weather=day.get('nightweather', ''),
                        day_temp=day.get('daytemp', '0'),
                        night_temp=day.get('nighttemp', '0'),
                        wind_direction=day.get('daywind', ''),
                        wind_power=day.get('daypower', '')
                    ))
        
        print(f"[WEATHER] 天气查询完成: 城市={city}, 结果数={len(weather_list)}")
        return weather_list
    
    def geocode(self, address: str, city: str = "") -> Optional[Location]:
        """地理编码: 将地址转换为坐标
        
        API: https://restapi.amap.com/v3/geocode/geocode
        
        Args:
            address: 地址字符串
            city: 城市名称
            
        Returns:
            Location 对象，失败返回 None
        """
        params = {
            'address': address,
        }
        if city:
            params['city'] = city
        
        try:
            data = self._get('geocode/geocode', params)
            geocodes = data.get('geocodes', [])
            
            if not geocodes:
                return None
            
            location_str = geocodes[0].get('location', '')
            if not location_str or ',' not in location_str:
                return None
            
            lng, lat = location_str.split(',')
            return Location(longitude=float(lng), latitude=float(lat))
            
        except Exception as e:
            print(f"[WARNING] 地理编码失败: {address}, 错误: {e}")
            return None
    
    def regeocode(self, longitude: float, latitude: float) -> Optional[str]:
        """逆地理编码: 将坐标转换为地址
        
        API: https://restapi.amap.com/v3/geocode/regeocode
        
        Args:
            longitude: 经度
            latitude: 纬度
            
        Returns:
            地址字符串，失败返回 None
        """
        params = {
            'location': f"{longitude},{latitude}",
            'poitype': '',  # 附近POI类型
            'radius': 1000,  # 搜索半径
            'extensions': 'base',  # 返回基本信息
            'batch': 'false',
        }
        
        try:
            data = self._get('geocode/regeocode', params)
            regeocode = data.get('regeocode', {})
            return regeocode.get('formatted_address', '')
            
        except Exception as e:
            print(f"[WARNING] 逆地理编码失败: ({longitude},{latitude}), 错误: {e}")
            return None


# ============================================
# 服务单例
# ============================================

_direct_service: Optional[AmapDirectService] = None


def get_amap_direct_service() -> AmapDirectService:
    """获取全局高德地图直接服务单例"""
    global _direct_service
    if _direct_service is None:
        _direct_service = AmapDirectService()
    return _direct_service
