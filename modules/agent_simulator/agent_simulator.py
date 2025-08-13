"""
智能体模拟器
负责模拟智能体的行为和决策
"""

import json
import re
from typing import Dict, Any, List
import logging

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
            
            # 准备工具列表
            # tools_list = self._format_tools_for_agent()
            
            system_prompt = self.current_agent_config.system_prompt
            # 构建用户提示词
            user_prompt = f"对话历史：\n{conversation_history}\n\n请根据对话历史生成响应。"
            
            # 调用LLM生成响应
            response = self.llm_client.generate_completion(
                prompt=user_prompt,
                system_prompt=system_prompt
            )
            
            response_content = response.content.strip()
            
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
    
    def _format_tools_for_agent(self) -> str:
        """格式化工具信息给智能体"""
        try:
            tools_text = []
            
            for tool_id in self.current_agent_config.tools:
                tool_info = self.tools_info.get(tool_id)
                if tool_info:
                    tool_name = tool_info.get('name', tool_id)
                    tool_desc = tool_info.get('description', '')
                    parameters = tool_info.get('parameters', [])
                    
                    # 构建参数信息
                    param_list = []
                    for param in parameters:
                        param_name = param.get('name', '')
                        param_type = param.get('type', '')
                        param_desc = param.get('description', '')
                        required = param.get('required', False)
                        
                        param_info = f"  - {param_name} ({param_type})"
                        if required:
                            param_info += " [必填]"
                        param_info += f": {param_desc}"
                        param_list.append(param_info)
                    
                    # 构建工具描述
                    tool_text = f"**{tool_name}**\n功能：{tool_desc}"
                    if param_list:
                        tool_text += "\n参数：\n" + "\n".join(param_list)
                    
                    tools_text.append(tool_text)
            
            return "\n\n".join(tools_text)
            
        except Exception as e:
            self.logger.error(f"Failed to format tools: {e}")
            return "工具信息不可用"
    
    def _contains_tool_call(self, response_content: str) -> bool:
        """
        判断响应是否包含工具调用
        检查是否包含```json ... ```格式的工具调用
        
        Args:
            response_content: 响应内容
            
        Returns:
            是否包含工具调用
        """
        try:
            # 检查是否包含JSON代码块
            json_pattern = r'```json\s*(.*?)\s*```'
            match = re.search(json_pattern, response_content, re.DOTALL)
            
            if match:
                json_content = match.group(1).strip()
                try:
                    # 尝试解析JSON内容
                    parsed_json = json.loads(json_content)
                    
                    # 检查是否是有效的工具调用格式
                    if isinstance(parsed_json, dict) and 'name' in parsed_json:
                        return True
                    
                except json.JSONDecodeError:
                    return False
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to check tool call: {e}")
            return False
