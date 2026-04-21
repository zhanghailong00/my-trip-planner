"""配置管理模块

使用 Pydantic Settings 管理应用配置，支持从 .env 文件加载
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类
    
    配置项优先级: 环境变量 > .env文件 > 默认值
    """
    
    model_config = SettingsConfigDict(
        env_file="../.env",         # 指向根目录的 .env
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ============================================
    # 高德地图配置
    # ============================================
    amap_api_key: str = ""                    # 高德地图 API Key
    amap_security_code: str = ""               # 高德地图安全密钥
    amap_provider: str = "mcp"                # 地图服务提供者 (mcp/direct)
    amap_mcp_timeout: int = 60                # MCP 调用超时时间(秒)
    
    # ============================================
    # LLM 大语言模型配置
    # ============================================
    llm_provider: str = "deepseek"            # LLM 提供者
    llm_model: str = "deepseek-chat"          # 模型名称
    llm_temperature: float = 0.7              # 生成温度 (0-1)
    
    # OpenAI 配置
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    
    # DeepSeek 配置
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    
    # ============================================
    # 应用配置
    # ============================================
    app_name: str = "My Trip Planner"
    app_version: str = "1.0.0"
    api_base_url: str = "http://localhost:8001"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    
    def get_cors_origins_list(self) -> list[str]:
        """将逗号分隔的CORS配置转为列表"""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    def get_amap_mcp_command_list(self) -> list[str]:
        """获取高德地图MCP服务的启动命令
        
        使用 uvx 运行官方 amap-mcp-server
        uvx 会自动从 pip 安装并运行
        """
        return [
            "uvx",                          # uv 的工具运行器
            "amap-mcp-server",              # 高德地图MCP服务包名
        ]
    
    def validate_config(self) -> bool:
        """验证必要配置是否完整
        
        Returns:
            bool: 配置是否有效
            
        Raises:
            ValueError: 当必要配置缺失时
        """
        errors = []
        
        # 检查高德地图 API Key
        if not self.amap_api_key or self.amap_api_key == "your_amap_api_key_here":
            errors.append("AMAP_API_KEY 未配置或为占位符")
        
        # 检查 LLM API Key
        if self.llm_provider == "deepseek":
            if not self.deepseek_api_key or self.deepseek_api_key == "your_deepseek_api_key_here":
                errors.append("DEEPSEEK_API_KEY 未配置或为占位符")
        elif self.llm_provider == "openai":
            if not self.openai_api_key or self.openai_api_key == "your_openai_api_key_here":
                errors.append("OPENAI_API_KEY 未配置或为占位符")
        
        if errors:
            raise ValueError("\n".join(errors))
        
        return True


# 全局配置单例 (延迟加载)
_settings: Settings | None = None


def get_settings() -> Settings:
    """获取全局配置单例
    
    使用延迟加载确保配置在应用启动时正确初始化
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def validate_config() -> bool:
    """验证配置的便捷函数"""
    return get_settings().validate_config()


def print_config() -> None:
    """打印当前配置 (隐藏敏感信息)"""
    settings = get_settings()
    print("\n--- Current Configuration ---")
    print(f"  App Name: {settings.app_name}")
    print(f"  App Version: {settings.app_version}")
    print(f"  LLM Provider: {settings.llm_provider}")
    print(f"  LLM Model: {settings.llm_model}")
    print(f"  Map Provider: {settings.amap_provider}")
    print(f"  AMAP API Key: {'[OK]' if settings.amap_api_key else '[MISSING]'}")
    
    if settings.llm_provider == "deepseek":
        api_key_status = '[OK]' if settings.deepseek_api_key else '[MISSING]'
        print(f"  DeepSeek API Key: {api_key_status}")
    elif settings.llm_provider == "openai":
        api_key_status = '[OK]' if settings.openai_api_key else '[MISSING]'
        print(f"  OpenAI API Key: {api_key_status}")
