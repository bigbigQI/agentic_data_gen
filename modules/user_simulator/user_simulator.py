"""
用户模拟器
负责模拟真实用户与智能体进行多轮对话交互
"""

import json
from typing import Dict, Any
import logging

from core.base_module import BaseModule
from core.models import Task, UserPersona
from core.exceptions import AgentDataGenException
from utils.llm_client import LLMClient
from config.prompts.user_prompts import UserPrompts
from .user_persona_generator import UserPersonaGenerator


class UserSimulator(BaseModule):
    """用户模拟器"""
    
    def __init__(self, config: Dict[str, Any] = None, logger: logging.Logger = None):
        """
        初始化用户模拟器
        
        Args:
            config: 配置字典
            logger: 日志器
        """
        super().__init__(config, logger)
        
        self.llm_client = None
        self.persona_generator = None
        self.prompts = UserPrompts()
        
        # 当前状态
        self.current_persona = None
        self.current_task = None
        
    def _setup(self):
        """设置组件"""
        from config.settings import settings
        
        # 初始化LLM客户端
        llm_config = settings.get_llm_config()
        llm_config['provider'] = settings.DEFAULT_LLM_PROVIDER
        self.llm_client = LLMClient(llm_config, self.logger)
        
        # 初始化人格生成器
        self.persona_generator = UserPersonaGenerator(logger=self.logger)
        self.persona_generator.initialize()
    
    def initialize_for_task(self, task: Task, user_persona: UserPersona):
        """
        为任务初始化用户模拟器
        
        Args:
            task: 任务对象
            user_persona: 用户人格
        """
        self.current_task = task
        self.current_persona = user_persona
        self.logger.info(f"Initialized user simulator for task {task.id} with persona {user_persona.id}")
    
    def generate_initial_message(self) -> str:
        """生成初始用户消息"""
        try:
            if not self.current_task or not self.current_persona:
                raise AgentDataGenException("No active task or persona for message generation")
            
            # 构建用户特征描述
            user_characteristics = self.prompts.USER_CHARACTERISTICS_TEMPLATE.format(
                personality_description=self.current_persona.metadata.get('personality_description', ''),
                style_description=self.current_persona.metadata.get('style_description', '')
            )
            
            # 构建系统提示词
            system_prompt = self.prompts.USER_SIMULATION_SYSTEM.format(
                user_characteristics=user_characteristics,
                task_instruction=self.current_task.description
            )
            
            # 生成初始消息
            response = self.llm_client.generate_completion(
                prompt=self.prompts.INIT_CONVERSATION,
                system_prompt=system_prompt
            )
            
            return response.content.strip()
            
        except Exception as e:
            self.logger.error(f"Failed to generate initial message: {e}")
            return "你好，我需要一些帮助。"  # 回退到默认消息
    
    def respond_to_agent(self, agent_message: str, conversation_history: str = "") -> str:
        """
        响应智能体的消息
        
        Args:
            agent_message: 智能体发送的消息
            conversation_history: 对话历史
            
        Returns:
            用户的响应消息
        """
        try:
            if not self.current_persona or not self.current_task:
                raise AgentDataGenException("No active persona or task for response generation")
            
            # 构建用户特征描述
            user_characteristics = self.prompts.USER_CHARACTERISTICS_TEMPLATE.format(
                personality_description=self.current_persona.metadata.get('personality_description', ''),
                style_description=self.current_persona.metadata.get('style_description', '')
            )
            
            # 构建系统提示词
            system_prompt = self.prompts.USER_SIMULATION_SYSTEM.format(
                user_characteristics=user_characteristics,
                task_instruction=self.current_task.description
            )
            
            # 构建用户提示词
            user_prompt = self.prompts.USER_RESPONSE_PROMPT.format(
                conversation_history=conversation_history
            )
            
            # 生成响应
            response = self.llm_client.generate_completion(
                prompt=user_prompt,
                system_prompt=system_prompt
            )
            user_response = response.content.strip()
            
            return user_response
            
        except Exception as e:
            self.logger.error(f"Failed to generate user response: {e}")
            return "好的，我明白了。"