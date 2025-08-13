"""
Agent合成模块
负责基于现有的工具库生成多样化的智能体配置
"""

from .tool_graph import ToolGraph
from .tool_combination_generator import ToolCombinationGenerator
from .agent_config_generator import AgentConfigGenerator

from core.base_module import BaseModule
from typing import Dict, Any, List
import logging


class AgentSynthesizerModule(BaseModule):
    """智能体合成模块主类"""
    
    def __init__(self, config: Dict[str, Any] = None, logger: logging.Logger = None):
        """
        初始化智能体合成模块
        
        Args:
            config: 模块配置
            logger: 日志器
        """
        super().__init__(config, logger)
        
        # 初始化子组件
        self.tool_combination_generator = None
        self.agent_config_generator = None
    
    def _setup(self):
        """设置模块组件"""
        self.tool_combination_generator = ToolCombinationGenerator(
            self.config.get('tool_combination_generator', {}), self.logger
        )
        self.agent_config_generator = AgentConfigGenerator(
            self.config.get('agent_config_generator', {}), self.logger
        )
        
        # 初始化子组件
        self.tool_combination_generator.initialize()
        self.agent_config_generator.initialize()
    
    def process(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        处理智能体合成
        
        Args:
            input_data: 输入数据，包含tools等信息
            **kwargs: 其他参数
            
        Returns:
            生成的智能体配置数据
        """
        try:
            tools = input_data.get('tools', [])
            target_agent_count = input_data.get('target_agent_count', 1000)
            
            if not tools:
                raise ValueError("No tools provided for agent synthesis")
            
            self.logger.info(f"Starting agent synthesis with {len(tools)} tools, target: {target_agent_count} agents")
            
            # 1. 生成工具组合（基于场景内相似度图和随机游走）
            self.logger.info("Generating tool combinations using graph-based random walk...")
            tool_combinations = self.tool_combination_generator.process({
                'tools': tools,
                'target_count': target_agent_count
            })
            
            # 2. 创建工具数据映射
            tools_data = {tool['id']: tool for tool in tools}
            
            # 3. 生成智能体配置
            agents = self.agent_config_generator.process({
                'tool_combinations': tool_combinations,
                'tools_data': tools_data
            })
            
            self.logger.info(f"Successfully generated {len(agents)} agent configurations")
            
            return {
                'agents': agents,
                'tool_combinations': tool_combinations,
                'stats': {
                    'agent_count': len(agents),
                    'tool_combinations_count': len(tool_combinations),
                    'avg_tools_per_agent': sum(len(combo['tool_ids']) for combo in tool_combinations) / len(tool_combinations) if tool_combinations else 0,
                    'unique_tools_used': len(set(tool_id for combo in tool_combinations for tool_id in combo['tool_ids'])),
                    'agent_generation_success_rate': len(agents) / len(tool_combinations) if tool_combinations else 0,
                    'generation_method': 'fixed_template_simple'
                }
            }
            
        except Exception as e:
            self.logger.error(f"Agent synthesis failed: {e}")
            raise


# 配置常量
DEFAULT_TOOL_COUNT_RANGE = (3, 6)
DEFAULT_AGENT_COUNT = 1000
DEFAULT_SIMILARITY_THRESHOLD = 0.7
DEFAULT_EMBEDDING_DIMENSIONS = 256

__all__ = [
    'AgentSynthesizerModule',
    'ToolGraph',
    'ToolCombinationGenerator',
    'AgentConfigGenerator',
    'DEFAULT_TOOL_COUNT_RANGE',
    'DEFAULT_AGENT_COUNT', 
    'DEFAULT_SIMILARITY_THRESHOLD',
    'DEFAULT_EMBEDDING_DIMENSIONS'
]