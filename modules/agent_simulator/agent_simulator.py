"""
智能体模拟器
负责模拟智能体的行为和决策
"""

import json
import re
from typing import Dict, Any, List
import logging


import sys
from pathlib import Path

from core.base_module import BaseModule
from core.models import AgentConfig
from core.exceptions import AgentDataGenException
from utils.llm_client import LLMClient
from config.prompts.agent_prompts import AgentPrompts


class AgentSimulator(BaseModule):
    """智能体模拟器"""
    
    def __init__(self, config: Dict[str, Any] = None, logger: logging.Logger = None):
        """
        初始化智能体模拟器
        
        Args:
            config: 配置字典
            logger: 日志器
        """
        super().__init__(config, logger)
        
        self.llm_client = None
        self.prompts = AgentPrompts()
        
        # 当前状态
        self.current_agent_config = None
        self.tools_info = {}
        
    def _setup(self):
        """设置组件"""
        from config.settings import settings
        
        # 初始化LLM客户端
        llm_config = settings.get_llm_config()
        llm_config['provider'] = settings.DEFAULT_LLM_PROVIDER
        self.llm_client = LLMClient(llm_config, self.logger)
    
    def initialize_for_agent(self, agent_config: AgentConfig, tools_info: Dict[str, Any]):
        """
        为智能体初始化模拟器
        
        Args:
            agent_config: 智能体配置
            tools_info: 工具信息
        """
        self.current_agent_config = agent_config
        self.tools_info = tools_info
        self.logger.info(f"Initialized agent simulator for agent {agent_config.id}")
    
    def respond(self, conversation_history: str) -> Dict[str, Any]:
        """
        根据对话历史生成智能体响应
        参考other_project_fils中的APIAgent_turn实现
        
        Args:
            conversation_history: 对话历史
            
        Returns:
            包含sender、recipient、message的响应字典
        """
        try:
            if not self.current_agent_config:
                raise AgentDataGenException("No agent configuration set")
            
            
            system_prompt = self.current_agent_config.system_prompt
            # 构建用户提示词
            user_prompt = self.prompts.AGENT_USER.format(conversation_history=conversation_history)
            # 调用LLM生成响应
            response = self.llm_client.generate_completion(
                prompt=user_prompt,
                system_prompt=system_prompt
            )
            
            response_content = response.content.strip()
            print("response_content", response_content)
            # 构建当前消息
            current_message = {"sender": "agent"}
            
            # 判断是否包含工具调用
            # 参考other_project_fils的逻辑
            if self._contains_tool_call(response_content):
                current_message["recipient"] = "execution"
                current_message["message"] = response_content
            else:
                current_message["recipient"] = "user"
                current_message["message"] = response_content
            
            return current_message
            
        except Exception as e:
            self.logger.error(f"Failed to generate agent response: {e}")
            return {
                "sender": "agent",
                "recipient": "user",
                "message": "抱歉，我遇到了一些问题，请稍后再试。"
            }
    
    def _contains_tool_call(self, response_content: str) -> bool:
        """
        判断响应是否包含工具调用
        支持多种格式：```json ... ```、``` ... ```、普通JSON对象
        
        Args:
            response_content: 响应内容
            
        Returns:
            是否包含工具调用
        """
        try:
            # 1. 首先尝试解析 ```json ... ``` 格式
            json_code_pattern = r'```json\s*(.*?)\s*```'
            match = re.search(json_code_pattern, response_content, re.DOTALL)
            
            if match:
                json_content = match.group(1).strip()
                if self._is_valid_tool_call_json(json_content):
                    return True
            
            # 2. 尝试解析 ``` ... ``` 格式（不指定语言）
            code_block_pattern = r'```\s*(.*?)\s*```'
            match = re.search(code_block_pattern, response_content, re.DOTALL)
            
            if match:
                code_content = match.group(1).strip()
                if self._is_valid_tool_call_json(code_content):
                    return True
            
            # 3. 尝试提取普通的 JSON 对象
            # 改进的正则表达式，更好地处理嵌套JSON
            json_object_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            json_matches = re.finditer(json_object_pattern, response_content)
            
            for match in json_matches:
                json_str = match.group(0)
                if self._is_valid_tool_call_json(json_str):
                    return True
            
            # 4. 尝试提取单行JSON（处理可能的换行符）
            # 移除换行符和多余空格后尝试解析
            cleaned_content = re.sub(r'\s+', ' ', response_content.strip())
            if self._is_valid_tool_call_json(cleaned_content):
                return True
                
            return False

        except Exception as e:
            self.logger.error(f"Failed to check tool call: {e}")
            return False
    
    def _is_valid_tool_call_json(self, json_str: str) -> bool:
        """
        验证JSON字符串是否为有效的工具调用格式
        
        Args:
            json_str: JSON字符串
            
        Returns:
            是否为有效的工具调用
        """
        try:
            parsed_json = json.loads(json_str)
            
            # 检查是否为字典类型
            if not isinstance(parsed_json, dict):
                return False
            
            # 检查是否包含必要的字段
            if 'name' not in parsed_json:
                return False
            
            # 检查name字段是否为字符串且不为空
            if not isinstance(parsed_json['name'], str) or not parsed_json['name'].strip():
                return False
            
            # 检查arguments字段（如果存在）
            if 'arguments' in parsed_json:
                if not isinstance(parsed_json['arguments'], dict):
                    return False
            
            return True
            
        except (json.JSONDecodeError, TypeError, KeyError):
            return False

if __name__ == "__main__":
    # 注意拼写：AgentSimulator
    from modules.agent_simulator.agent_simulator import AgentSimulator

    # 创建模拟器实例（此处logger可为None或自定义）
    simulator = AgentSimulator(logger=None)

    # 测试字符串
    test_str = '{"name": "tag_department_codes", "arguments": {"department_map": {"user_7xK2m": "Sales", "user_9pL4q": "Marketing", "user_2wN8r": "Product", "user_5hJ1k": "Sales", "user_3dF6v": "Marketing"}}}'
    result = simulator._contains_tool_call(test_str)
    test_str = '{"name": "generate_dept_invoice", "arguments": {"session_token": "sess_admin_aXyZ9", "date": "2024-05-31"}}'
    # 调用_contains_tool_call方法
    result = simulator._contains_tool_call(test_str)

    print(f"Tool call detected: {result}")