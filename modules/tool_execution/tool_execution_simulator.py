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
            
            return execution_results
            
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
        Extract tool calls from agent message.

        Args:
            agent_message: The message from the agent.

        Returns:
            List of tool calls, each as a dict {'name': str, 'arguments': dict}
        """
        import re
        import json

        def is_valid_tool_call_json(json_str: str) -> bool:
            try:
                parsed_json = json.loads(json_str)
                if not isinstance(parsed_json, dict):
                    return False
                if 'name' not in parsed_json:
                    return False
                if not isinstance(parsed_json['name'], str) or not parsed_json['name'].strip():
                    return False
                if 'arguments' in parsed_json and not isinstance(parsed_json['arguments'], dict):
                    return False
                return True
            except (json.JSONDecodeError, TypeError, KeyError):
                return False

        try:
            tool_calls = []
            processed_json_strings = set()

            # 1. Extract ```json ... ``` code blocks
            json_code_pattern = r'```json\s*(.*?)\s*```'
            matches = re.findall(json_code_pattern, agent_message, re.DOTALL)
            for match in matches:
                json_content = match.strip()
                if json_content in processed_json_strings:
                    continue
                processed_json_strings.add(json_content)
                try:
                    parsed_json = json.loads(json_content)
                    if isinstance(parsed_json, dict) and is_valid_tool_call_json(json_content):
                        tool_calls.append(parsed_json)
                    elif isinstance(parsed_json, list):
                        for item in parsed_json:
                            if isinstance(item, dict) and 'name' in item and is_valid_tool_call_json(json.dumps(item)):
                                tool_calls.append(item)
                except Exception:
                    continue

            # 2. Extract ``` ... ``` code blocks (no language specified)
            code_block_pattern = r'```\s*(.*?)\s*```'
            matches_code = re.findall(code_block_pattern, agent_message, re.DOTALL)
            for match in matches_code:
                code_content = match.strip()
                if code_content in processed_json_strings:
                    continue
                processed_json_strings.add(code_content)
                try:
                    parsed_json = json.loads(code_content)
                    if isinstance(parsed_json, dict) and is_valid_tool_call_json(code_content):
                        tool_calls.append(parsed_json)
                    elif isinstance(parsed_json, list):
                        for item in parsed_json:
                            if isinstance(item, dict) and 'name' in item and is_valid_tool_call_json(json.dumps(item)):
                                tool_calls.append(item)
                except Exception:
                    continue

            # 3. Remove all processed code blocks from message
            remaining_message = agent_message
            for match in matches:
                json_block = f"```json{match}```"
                remaining_message = remaining_message.replace(json_block, " ")
            for match in matches_code:
                code_block = f"```{match}```"
                remaining_message = remaining_message.replace(code_block, " ")

            # 4. Extract JSON objects {...}
            json_object_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            json_matches = re.finditer(json_object_pattern, remaining_message)
            for match in json_matches:
                json_str = match.group(0)
                if json_str in processed_json_strings:
                    continue
                processed_json_strings.add(json_str)
                if is_valid_tool_call_json(json_str):
                    try:
                        parsed_json = json.loads(json_str)
                        tool_calls.append(parsed_json)
                    except Exception:
                        continue

            # 5. Extract JSON arrays [...]
            json_array_pattern = r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]'
            array_matches = re.finditer(json_array_pattern, remaining_message)
            for match in array_matches:
                json_str = match.group(0)
                if json_str in processed_json_strings:
                    continue
                processed_json_strings.add(json_str)
                try:
                    parsed_json = json.loads(json_str)
                    if isinstance(parsed_json, list):
                        for item in parsed_json:
                            if isinstance(item, dict) and 'name' in item and is_valid_tool_call_json(json.dumps(item)):
                                tool_calls.append(item)
                except Exception:
                    continue

            # 6. Try to parse the whole message (after removing code blocks) as JSON (single line, fallback)
            cleaned_content = re.sub(r'\s+', ' ', remaining_message.strip())
            if cleaned_content not in processed_json_strings and is_valid_tool_call_json(cleaned_content):
                try:
                    parsed_json = json.loads(cleaned_content)
                    if isinstance(parsed_json, dict):
                        tool_calls.append(parsed_json)
                    elif isinstance(parsed_json, list):
                        for item in parsed_json:
                            if isinstance(item, dict) and 'name' in item and is_valid_tool_call_json(json.dumps(item)):
                                tool_calls.append(item)
                except Exception:
                    pass

            return tool_calls

        except Exception as e:
            self.logger.error(f"Failed to extract tool calls from message: {e}")
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