"""
场景与工具生成模块
负责生成应用场景和相关工具
"""

from .scenario_generator import ScenarioGenerator
from .tool_designer import ToolDesigner
# from .tool_registry import ToolRegistry
from .tool_embedding import ToolEmbedding
# from core.base_module import BaseModule
# from typing import Dict, Any, List
# import logging


# class DomainToolGeneratorModule(BaseModule):
#     """场景与工具生成模块主类"""
    
#     def __init__(self, config: Dict[str, Any] = None, logger: logging.Logger = None):
#         """
#         初始化场景与工具生成模块
        
#         Args:
#             config: 模块配置
#             logger: 日志器
#         """
#         super().__init__(config, logger)
        
#         # 初始化子组件
#         self.scenario_generator = None
#         self.tool_designer = None
#         self.tool_registry = None
#         self.semantic_validator = None
    
#     def _setup(self):
#         """设置模块组件"""
#         self.scenario_generator = ScenarioGenerator(self.config.get('scenario_generator', {}), self.logger)
#         self.tool_designer = ToolDesigner(self.config.get('tool_designer', {}), self.logger)
#         # self.tool_registry = ToolRegistry(self.config.get('tool_registry', {}), self.logger)
        
#         # 初始化子组件
#         self.scenario_generator.initialize()
#         self.tool_designer.initialize()
#         self.tool_registry.initialize()
    
#     def process(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
#         """
#         处理场景与工具生成
        
#         Args:
#             input_data: 输入数据，包含domains等信息
#             **kwargs: 其他参数
            
#         Returns:
#             生成的场景和工具数据
#         """
#         try:
#             domains = input_data.get('domains', [])
#             target_scenario_count = input_data.get('target_scenario_count', 100)
#             target_tool_count = input_data.get('target_tool_count', 500)
            
#             self.logger.info(f"Starting domain-tool generation for {len(domains)} domains")
            
#             # 1. 生成场景
#             self.logger.info("Generating scenarios...")
#             scenarios = self.scenario_generator.process({
#                 'domains': domains,
#                 'target_count': target_scenario_count
#             })
            
#             # 2. 基于场景生成工具
#             self.logger.info("Generating tools...")
#             tools = self.tool_designer.process({
#                 'scenarios': scenarios,
#                 'target_count': target_tool_count
#             })
            
#             # 3. 注册工具
#             self.logger.info("Registering tools...")
#             self.tool_registry.process({'tools': tools})
            
#             return {
#                 'scenarios': scenarios,
#                 'tools': tools,
#                 'validation_results': validation_results,
#                 'stats': {
#                     'scenario_count': len(scenarios),
#                     'tool_count': len(tools),
#                     'domain_count': len(domains)
#                 }
#             }
            
#         except Exception as e:
#             self.logger.error(f"Domain-tool generation failed: {e}")
#             raise


__all__ = [
    # 'DomainToolGeneratorModule',
    'ScenarioGenerator',
    'ToolDesigner', 
    # 'ToolRegistry',
    'ToolEmbedding'
] 