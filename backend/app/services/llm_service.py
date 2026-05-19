"""LLM (大语言模型) 服务封装

支持多种 LLM 提供者: OpenAI, DeepSeek, SiliconFlow 等

通过 LangChain 的 ChatOpenAI 接口统一调用，保持 API 一致性
"""

import logging
from typing import Optional

from langchain_openai import ChatOpenAI

from ..config import get_settings

logger = logging.getLogger(__name__)


class LLMService:
    """大语言模型服务封装类
    
    基于 LangChain 的 ChatOpenAI 接口，支持多种 LLM 提供者
    通过统一的 base_url 配置切换不同的 provider
    
    Attributes:
        llm: LangChain 的 ChatOpenAI 实例
        provider: 当前使用的 LLM 提供者名称
        model: 当前使用的模型名称
    """
    
    def __init__(self):
        """初始化 LLM 服务
        
        根据配置创建对应的 ChatOpenAI 实例
        """
        settings = get_settings()
        self.provider = settings.llm_provider
        self.model = settings.llm_model
        
        # 根据 provider 选择对应的配置
        if self.provider == "deepseek":
            api_key = settings.deepseek_api_key
            base_url = settings.deepseek_base_url
        elif self.provider == "openai":
            api_key = settings.openai_api_key
            base_url = settings.openai_base_url
        else:
            # 默认使用 OpenAI 兼容接口
            api_key = settings.openai_api_key
            base_url = settings.openai_base_url
        
        # 检查 API Key
        if not api_key:
            raise ValueError(
                f"{self.provider} API Key 未配置，"
                f"请在 .env 文件中设置 {self.provider.upper()}_API_KEY"
            )
        
        # 创建 LangChain ChatOpenAI 实例
        # 注意: LangChain 的 ChatOpenAI 实际支持任何 OpenAI 兼容 API
        self.llm = ChatOpenAI(
            model=self.model,
            api_key=api_key,
            base_url=base_url,
            temperature=settings.llm_temperature,
            streaming=False,  # 禁用流式输出，简化处理
        )

        logger.info("[SUCCESS] LLM服务初始化成功: provider=%s, model=%s", self.provider, self.model)
    
    def invoke(self, prompt: str) -> str:
        """调用 LLM 生成回复
        
        Args:
            prompt: 输入的提示词/对话内容
            
        Returns:
            LLM 生成的文本回复
        """
        response = self.llm.invoke(prompt)
        return response.content if hasattr(response, "content") else str(response)
    
    def invoke_with_messages(self, messages: list) -> str:
        """使用消息列表调用 LLM
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
                     或 LangChain 的 Message 对象
                     
        Returns:
            LLM 生成的文本回复
        """
        response = self.llm.invoke(messages)
        return response.content if hasattr(response, "content") else str(response)


# ============================================
# 服务单例
# ============================================

_llm_service: Optional[LLMService] = None


def get_llm() -> LLMService:
    """获取全局 LLM 服务单例
    
    使用延迟加载确保配置先初始化
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
