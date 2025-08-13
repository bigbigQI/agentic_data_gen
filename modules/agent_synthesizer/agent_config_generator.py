"""
智能体配置生成器
整合工具组合和提示词，生成完整的智能体配置
"""

import random
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from core.base_module import BaseModule
from core.models import AgentConfig
from core.exceptions import AgentDataGenException
from utils.data_processor import DataProcessor
from utils.file_manager import FileManager


class AgentConfigGenerator(BaseModule):
    """智能体配置生成器"""
    
    def __init__(self, config: Dict[str, Any] = None, logger: logging.Logger = None):
        """
        初始化智能体配置生成器
        
        Args:
            config: 配置字典
            logger: 日志器
        """
        super().__init__(config, logger)
        
        self.data_processor = None
        self.file_manager = None
        
    def _setup(self):
        """设置组件"""
        from config.settings import settings
        
        # 初始化数据处理器
        self.data_processor = DataProcessor(self.logger)
        
        # 初始化文件管理器
        data_path = settings.get_data_path('agents')
        self.file_manager = FileManager(data_path, self.logger)
    
    def process(self, input_data: Dict[str, Any], **kwargs) -> List[AgentConfig]:
        """
        生成智能体配置
        
        Args:
            input_data: 包含工具组合的输入数据
            **kwargs: 其他参数
            
        Returns:
            智能体配置列表
        """
        try:
            tool_combinations = input_data.get('tool_combinations', [])
            tools_data = input_data.get('tools_data', {})
            
            if not tool_combinations:
                raise AgentDataGenException("No tool combinations provided")
            
            self.logger.info(f"Generating agent configurations for {len(tool_combinations)} combinations")
            
            agents = []
            for i, combination in enumerate(tool_combinations):
                try:
                    agent = self._generate_agent_config(combination, tools_data)
                    if agent:
                        agents.append(agent)
                        
                except Exception as e:
                    self.logger.error(f"Failed to generate agent for combination {i}: {e}")
                    continue
            
            # 保存智能体配置
            self._save_agent_configs(agents)
            
            self.logger.info(f"Successfully generated {len(agents)} agent configurations")
            return agents
            
        except Exception as e:
            self.logger.error(f"Agent configuration generation failed: {e}")
            raise AgentDataGenException(f"Failed to generate agent configurations: {e}")
    
    def _generate_agent_config(self, combination: Dict[str, Any], 
                                     tools_data: Dict[str, Any]) -> Optional[AgentConfig]:
        """生成单个智能体配置"""
        
        try:
            # 1. 生成智能体ID
            agent_id = self.data_processor.generate_id('agent', combination)
            
            # 2. 获取工具列表
            tool_ids = combination.get('tool_ids', [])
            if not tool_ids:
                raise ValueError("No tools in combination")
            
            # 3. 生成系统提示词
            system_prompt = self._build_system_prompt_with_tools(tool_ids, tools_data)
            # 4. 创建AgentConfig对象
            agent_config = AgentConfig(
                id=agent_id,
                system_prompt=system_prompt,
                tools=tool_ids,
            )
            
            return agent_config
            
        except Exception as e:
            self.logger.error(f"Failed to generate agent config: {e}")
            return None
    
    def _build_system_prompt_with_tools(self, tool_ids: List[str], tools_data: Dict[str, Any]) -> str:
        """构建包含工具列表的系统提示词"""
        from config.prompts.agent_prompts import AgentPrompts
        
        # 获取工具详细信息
        tools_info = []
        for tool_id in tool_ids:
            if tool_id in tools_data:
                tools_info.append(tools_data[tool_id])
        
        # 构建工具列表文本
        tools_list = self._build_tools_list(tools_info)
        
        # 使用固定模板
        prompts = AgentPrompts()
        return prompts.AGENT_SYSTEM.format(tools_list=tools_list)
    
    def _build_tools_list(self, tools_info: List[Dict[str, Any]]) -> str:
        """构建JSON格式的工具列表"""
        import json
        
        tools_json_list = []
        
        for tool in tools_info:
            tool_name = tool.get('name', '')
            tool_desc = tool.get('description', '')
            parameters = tool.get('parameters', [])
            
            # 构建JSON Schema格式的工具定义
            tool_json = {
                "name": tool_name,
                "description": tool_desc,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
            
            # 处理参数
            for param in parameters:
                param_name = param.get('name', '')
                param_type = param.get('type', 'string')
                param_desc = param.get('description', '')
                required = param.get('required', False)
                enum_values = param.get('enum', None)
                
                # 构建参数定义
                param_def = {
                    "type": param_type,
                    "description": param_desc
                }
                
                # 添加枚举值（如果有）
                if enum_values:
                    param_def["enum"] = enum_values
                
                # 添加到properties
                tool_json["parameters"]["properties"][param_name] = param_def
                
                # 添加到required（如果是必填）
                if required:
                    tool_json["parameters"]["required"].append(param_name)
            
            # 格式化JSON并添加到列表
            tool_json_str = json.dumps(tool_json, ensure_ascii=False, indent=2)
            tools_json_list.append(tool_json_str)
        
        return '\n\n'.join(tools_json_list)

    
    def _save_agent_configs(self, agents: List[AgentConfig]):
        """保存智能体配置"""
        try:
            # 转换为可序列化的格式
            agents_data = []
            for agent in agents:
                agent_dict = {
                    'id': agent.id,
                    'system_prompt': agent.system_prompt,
                    'tools': agent.tools,
                    'created_at': agent.created_at.isoformat() if hasattr(agent, 'created_at') and agent.created_at else datetime.now().isoformat()
                }
                agents_data.append(agent_dict)
            
            # 保存主文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"agents_batch_{timestamp}.json"
            
            self.file_manager.save_json(agents_data, filename)
            
        except Exception as e:
            self.logger.error(f"Failed to save agent configs: {e}")
            raise AgentDataGenException(f"Failed to save agents: {e}")

    
