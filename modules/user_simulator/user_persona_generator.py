"""
用户人格生成器
负责生成多样化的用户人格配置
"""

import random
from typing import Dict, Any, List
import logging
from datetime import datetime

from core.base_module import BaseModule
from core.models import UserPersona, UserPersonalityType, InteractionStyle
from core.exceptions import AgentDataGenException
from utils.data_processor import DataProcessor
from utils.file_manager import FileManager
from config.prompts.user_prompts import UserPrompts


class UserPersonaGenerator(BaseModule):
    """用户人格生成器"""
    
    def __init__(self, config: Dict[str, Any] = None, logger: logging.Logger = None):
        """
        初始化用户人格生成器
        
        Args:
            config: 配置字典
            logger: 日志器
        """
        super().__init__(config, logger)
        
        self.data_processor = None
        self.file_manager = None
        self.prompts = UserPrompts()
        
        
    def _setup(self):
        """设置组件"""
        from config.settings import settings
        
        # 初始化数据处理器
        self.data_processor = DataProcessor(self.logger)
        
        # 初始化文件管理器
        data_path = settings.get_data_path('user_personas')
        self.file_manager = FileManager(data_path, self.logger)
    
    def process(self) -> UserPersona:
        """
        生成用户人格
        
        Args:
            input_data: 输入数据
            **kwargs: 其他参数
            
        Returns:
            生成的用户人格
        """
        
        return self._generate_single_persona()
    
    def _generate_single_persona(self) -> UserPersona:
        """生成单个用户人格"""
        try:
            # 随机选择人格类型和交互风格
            personality_type = random.choice(list(UserPersonalityType))
            style_type = random.choice(list(InteractionStyle))
            
            # 生成人格ID
            persona_id = self.data_processor.generate_id('user_persona', {
                'personality': personality_type.value,
                'style': style_type.value,
                'timestamp': datetime.now().isoformat()
            })
            
            # 生成人格名称
            name = f"{personality_type.value}_{style_type.value}_user"
            
            # 创建UserPersona对象
            persona = UserPersona(
                id=persona_id,
                name=name,
                personality_type=personality_type,
                style_type=style_type,
                metadata={
                    'personality_description': self.prompts.PERSONALITY_DESCRIPTIONS[personality_type.value],
                    'style_description': self.prompts.STYLE_DESCRIPTIONS[style_type.value],
                    'generated_at': datetime.now().isoformat()
                }
            )
            
            return persona
            
        except Exception as e:
            self.logger.error(f"Failed to generate single persona: {e}")
            return None
