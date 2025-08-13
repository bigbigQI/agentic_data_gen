"""
LLM API客户端
统一的大语言模型调用接口
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from openai import OpenAI

from core.exceptions import LLMApiError, ConfigurationError


@dataclass
class LLMResponse:
    """LLM响应数据模型"""
    content: str
    model: str
    usage: Dict[str, int]
    response_time: float
    metadata: Dict[str, Any]


class LLMClient:
    """统一的LLM API客户端"""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger = None):
        """
        初始化LLM客户端
        
        Args:
            config: LLM配置
            logger: 日志器
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.provider = config.get("provider", "openai")
        
        # 初始化客户端
        self._init_clients()
    
    def _init_clients(self):
        """初始化各个LLM提供商的客户端"""
        try:
            if self.provider == "openai":
                self._init_openai_client()
            else:
                raise ConfigurationError(f"Unsupported LLM provider: {self.provider}")
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize LLM client: {e}")
    
    def _init_openai_client(self):
        """初始化OpenAI客户端"""
        if not self.config.get("api_key"):
            raise ConfigurationError("OpenAI API key is required")
        
        # 创建OpenAI客户端实例
        client_kwargs = {"api_key": self.config["api_key"]}
        if self.config.get("base_url"):
            client_kwargs["base_url"] = self.config["base_url"]
            
        self.openai_client = OpenAI(**client_kwargs)
        self.openai_config = self.config
    
    def generate_completion(
        self,
        prompt: str,
        system_prompt: str = None,
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        **kwargs
    ) -> LLMResponse:
        """
        生成文本补全
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大令牌数
            **kwargs: 其他参数
            
        Returns:
            LLM响应
        """
        start_time = time.time()
        
        try:
            if self.provider == "openai":
                response = self._openai_completion(
                    prompt, system_prompt, model, temperature, max_tokens, **kwargs
                )
            else:
                raise LLMApiError(f"Unsupported provider: {self.provider}")
            
            response_time = time.time() - start_time
            
            # 包装响应
            llm_response = LLMResponse(
                content=response.get("content", ""),
                model=response.get("model", ""),
                usage=response.get("usage", {}),
                response_time=response_time,
                metadata=response.get("metadata", {})
            )
            
            self.logger.debug(f"LLM completion generated in {response_time:.2f}s")
            return llm_response
            
        except Exception as e:
            self.logger.error(f"LLM completion failed: {e}")
            raise LLMApiError(f"LLM API call failed: {e}")
    
    def _openai_completion(
        self,
        prompt: str,
        system_prompt: str = None,
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        **kwargs
    ) -> Dict[str, Any]:
        """OpenAI API调用"""
        model = model or self.openai_config.get("model", "gpt-4")
        temperature = temperature or self.openai_config.get("temperature", 0.7)
        max_tokens = max_tokens or self.openai_config.get("max_tokens", 2000)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return {
            "content": response.choices[0].message.content,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            } if response.usage else {},
            "metadata": {"finish_reason": response.choices[0].finish_reason}
        }

    def batch_generate(
        self,
        prompts: List[str],
        system_prompt: str = None,
        **kwargs
    ) -> List[LLMResponse]:
        """
        批量生成
        
        Args:
            prompts: 提示词列表
            system_prompt: 系统提示词
            **kwargs: 其他参数
            
        Returns:
            响应列表
        """
        responses = []
        for prompt in prompts:
            try:
                response = self.generate_completion(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    **kwargs
                )
                responses.append(response)
            except Exception as e:
                self.logger.error(f"Batch generation failed for prompt: {e}")
                # 可以选择跳过失败的请求或抛出异常
                continue
        
        return responses
    
    def parse_json_response(self, response: LLMResponse) -> Any:
        """
        解析JSON格式的响应
        
        Args:
            response: LLM响应
            
        Returns:
            解析后的JSON数据
        """
        try:
            # 尝试直接解析
            return json.loads(response.content)
        except json.JSONDecodeError:
            # 尝试提取代码块中的JSON
            content = response.content.strip()
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                if end != -1:
                    json_str = content[start:end].strip()
                    return json.loads(json_str)
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                if end != -1:
                    json_str = content[start:end].strip()
                    return json.loads(json_str)
            
            raise LLMApiError(f"Failed to parse JSON response: {content}")
    
    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的token数量
        
        Args:
            text: 输入文本
            
        Returns:
            估算的token数量
        """
        # 简单的token估算，实际项目中可能需要更精确的方法
        return len(text.split()) * 1.3  # 英文单词大约1.3倍
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计"""
        return {
            "provider": self.provider,
            "model": self.config.get("model", "unknown"),
            "total_requests": getattr(self, "_total_requests", 0),
            "total_tokens": getattr(self, "_total_tokens", 0)
        } 