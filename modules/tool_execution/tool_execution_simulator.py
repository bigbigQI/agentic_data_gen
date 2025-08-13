"""
工具执行模拟器
负责协调工具调用的解析、执行和状态管理
"""

import json
import re
from typing import Dict, Any, List
import logging

from core.base_module import BaseModule
from core.exceptions import AgentDataGenException
from .execution_engine import ExecutionEngine


class ToolExecutionSimulator(BaseModule):
    """工具执行模拟器"""
    
    def __init__(self, config: Dict[str, Any] = None, logger: logging.Logger = None):
        """
        初始化工具执行模拟器
        
        Args:
            config: 配置字典
            logger: 日志器
        """
        super().__init__(config, logger)
        
        self.execution_engine = None
        
    def _setup(self):
        """设置组件"""
        from config.settings import settings
        
        # 初始化执行引擎
        engine_config = settings.SIMULATOR_CONFIG
        self.execution_engine = ExecutionEngine(engine_config, self.logger)
        self.execution_engine.initialize()
    
    def process(self, input_data: Any = None, **kwargs) -> Dict[str, Any]:
        """
        处理输入数据
        
        Args:
            input_data: 输入数据，应该包含智能体消息
            **kwargs: 其他参数
            
        Returns:
            处理结果
        """
        try:
            if isinstance(input_data, str):
                # 如果输入是字符串，直接当作智能体消息处理
                agent_message = input_data
            elif isinstance(input_data, dict) and 'agent_message' in input_data:
                # 如果输入是字典，提取智能体消息
                agent_message = input_data['agent_message']
            else:
                return {'error': 'Invalid input data format'}
            
            # 执行工具调用
            results = self.execute_agent_message(agent_message)
            
            return {
                'success': True,
                'tool_execution_results': results,
                'message_count': len(results)
            }
            
        except Exception as e:
            self.logger.error(f"Tool execution simulator process failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'tool_execution_results': []
            }
    
    def initialize_tools(self, tools_info: Dict[str, Any]):
        """
        初始化工具信息
        
        Args:
            tools_info: 工具信息字典
        """
        if self.execution_engine:
            self.execution_engine.register_tools(tools_info)
            self.logger.info(f"Initialized {len(tools_info)} tools for execution")
    
    def execute_agent_message(self, agent_message: str) -> List[Dict[str, Any]]:
        """
        执行智能体消息中的工具调用
        
        Args:
            agent_message: 智能体消息
            
        Returns:
            工具执行结果列表
        """
        try:
            # 提取工具调用
            tool_calls = self._extract_tool_calls(agent_message)
            
            if not tool_calls:
                return []
            
            # 执行工具调用
            execution_data = {
                'tool_calls': tool_calls,
            }
            
            execution_results = self.execution_engine.process(execution_data)
            
            # 格式化结果
            formatted_results = self._format_results_for_agent(execution_results)
            
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}")
            return [{
                'tool_name': 'error',
                'status': 'failure',
                'message': f"Execution error: {e}",
                'result': None
            }]
    
    def _extract_tool_calls(self, agent_message: str) -> List[Dict[str, Any]]:
        """
        从智能体消息中提取工具调用
        
        Args:
            agent_message: 智能体消息
            
        Returns:
            工具调用列表，每个元素为字典格式 {'name': str, 'arguments': dict}
        """
        try:
            tool_calls = []
            
            # 检查是否包含JSON代码块
            json_pattern = r'```json\s*(.*?)\s*```'
            matches = re.findall(json_pattern, agent_message, re.DOTALL)
            
            for match in matches:
                json_content = match.strip()
                try:
                    # 尝试解析JSON内容
                    parsed_json = json.loads(json_content)
                    
                    # 检查是否是有效的工具调用格式
                    if isinstance(parsed_json, dict) and 'name' in parsed_json:
                        tool_calls.append(parsed_json)
                        
                except json.JSONDecodeError:
                    continue
            
            return tool_calls
            
        except Exception as e:
            self.logger.error(f"Failed to extract tool calls from message: {e}")
            return []
    
    def _format_results_for_agent(self, execution_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        格式化执行结果给智能体
        
        Args:
            execution_results: 原始执行结果
            
        Returns:
            格式化后的结果列表
        """
        try:
            formatted_results = []
            results = execution_results.get('results', [])
            
            for result in results:
                formatted_result = {
                    'tool_name': result.get('metadata', {}).get('tool_name', 'unknown'),
                    'status': result.get('status', 'unknown'),
                    'result': result.get('result'),
                    'message': result.get('message', ''),
                    'execution_time': result.get('metadata', {}).get('execution_time', 0)
                }
                formatted_results.append(formatted_result)
            
            # 添加错误信息
            errors = execution_results.get('errors', [])
            for error in errors:
                error_result = {
                    'tool_name': 'error',
                    'status': 'failure',
                    'result': None,
                    'message': error,
                    'execution_time': 0
                }
                formatted_results.append(error_result)
            
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"Failed to format results: {e}")
            return []
    
    def reset_execution_state(self):
        """重置执行状态"""
        if self.execution_engine:
            self.execution_engine.reset_execution_state()
            self.logger.info("Execution state reset")
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        if not self.execution_engine:
            return {}
        
        execution_state = self.execution_engine.get_execution_state()
        tool_usage = execution_state.get('tool_usage_count', {})
        
        return {
            'tool_usage_distribution': tool_usage,
            'execution_engine_state_size': len(str(execution_state)),
            'total_executions': sum(tool_usage.values()) if tool_usage else 0
        }