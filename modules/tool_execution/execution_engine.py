"""
工具执行引擎
负责解析和执行工具调用
"""

import json
import re
import ast
import random
import time
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime

from core.base_module import BaseModule
from core.exceptions import AgentDataGenException
from utils.llm_client import LLMClient
from utils.data_processor import DataProcessor
from config.prompts.execution_prompts import ExecutionPrompts


class ExecutionEngine(BaseModule):
    """工具执行引擎"""
    
    def __init__(self, config: Dict[str, Any] = None, logger: logging.Logger = None):
        """
        初始化执行引擎
        
        Args:
            config: 配置字典
            logger: 日志器
        """
        super().__init__(config, logger)
        
        self.llm_client = None
        self.data_processor = None
        self.prompts = ExecutionPrompts()
        
        # 执行状态
        self.execution_state = {}
        self.tools_registry = {}
        
        # 执行配置
        self.success_rate = 0.85
        self.partial_failure_rate = 0.10
        self.complete_failure_rate = 0.05
        self.randomness_level = 0.1
        
    def _setup(self):
        """设置组件"""
        from config.settings import settings
        
        # 初始化LLM客户端
        llm_config = settings.get_llm_config()
        llm_config['provider'] = settings.DEFAULT_LLM_PROVIDER
        self.llm_client = LLMClient(llm_config, self.logger)
        
        # 初始化数据处理器
        self.data_processor = DataProcessor(self.logger)
        
        # 更新执行配置
        simulator_config = settings.SIMULATOR_CONFIG
        self.success_rate = simulator_config.get('success_rate', 0.85)
        self.partial_failure_rate = simulator_config.get('partial_failure_rate', 0.10)
        self.complete_failure_rate = simulator_config.get('complete_failure_rate', 0.05)
        self.randomness_level = simulator_config.get('randomness_level', 0.1)
    
    def process(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        处理工具执行请求
        
        Args:
            input_data: 包含工具调用信息的数据
            **kwargs: 其他参数
            
        Returns:
            执行结果
        """
        try:
            tool_calls = input_data.get('tool_calls', [])
            
            if not tool_calls:
                return {'results': [], 'errors': ['No tool calls provided']}
            
            
            # 执行工具调用
            results = []
            errors = []
            
            for tool_call in tool_calls:
                try:
                    result = self.execute_tool_call(tool_call)
                    results.append(result)
                except Exception as e:
                    error_msg = f"Failed to execute tool call: {e}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Execution engine process failed: {e}")
            raise AgentDataGenException(f"Execution failed: {e}")
    
    def execute_tool_call(self, tool_call: str) -> Dict[str, Any]:
        """
        执行单个工具调用
        
        Args:
            tool_call: 工具调用信息
            
        Returns:
            执行结果
        """
        try:
            # 解析工具调用
            tool_name = tool_call.get('name')
            parameters = tool_call.get('arguments', {})
            # 获取工具信息
            tool_info = self.tools_registry.get(tool_name)
            if not tool_info:
                return self._create_error_result(
                    tool_name, 
                    f"Tool '{tool_name}' not found in registry",
                    'tool_not_found'
                )
            
            # 验证参数
            validation_result = self._validate_parameters(tool_info, parameters)
            if not validation_result['valid']:
                return self._create_error_result(
                    tool_name,
                    validation_result['error'],
                    'parameter_error'
                )
            
            # 决定执行结果类型
            execution_type = self._determine_execution_type()
            
            # 模拟执行
            result = self._simulate_execution(tool_call, tool_info, execution_type)
            
            # 更新执行状态
            self._update_execution_state(tool_name, parameters, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to execute tool call '{tool_call}': {e}")
            return self._create_error_result(
                'unknown',
                f"Execution error: {e}",
                'system_error'
            )

    def _validate_parameters(self, tool_info: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证工具参数"""
        try:
            tool_parameters = tool_info.get('parameters', [])
            required_params = [p['name'] for p in tool_parameters if p.get('required', True)]
            
            # 检查必需参数
            missing_params = [param for param in required_params if param not in parameters]
            if missing_params:
                return {
                    'valid': False,
                    'error': f"Missing required parameters: {missing_params}"
                }
            
            # 检查参数类型（简单验证）
            for param_info in tool_parameters:
                param_name = param_info['name']
                if param_name in parameters:
                    expected_type = param_info.get('type', 'string')
                    param_value = parameters[param_name]
                    
                    # 简单的类型检查
                    if expected_type == 'integer' and not isinstance(param_value, int):
                        try:
                            parameters[param_name] = int(param_value)
                        except (ValueError, TypeError):
                            return {
                                'valid': False,
                                'error': f"Parameter '{param_name}' should be an integer"
                            }
                    elif expected_type == 'number' and not isinstance(param_value, (int, float)):
                        try:
                            parameters[param_name] = float(param_value)
                        except (ValueError, TypeError):
                            return {
                                'valid': False,
                                'error': f"Parameter '{param_name}' should be a number"
                            }
            
            return {'valid': True}
            
        except Exception as e:
            return {
                'valid': False,
                'error': f"Parameter validation error: {e}"
            }
    
    def _determine_execution_type(self) -> str:
        """决定执行结果类型"""
        rand = random.random()
        
        if rand < self.success_rate:
            return 'success'
        elif rand < self.success_rate + self.partial_failure_rate:
            return 'partial_success'
        else:
            return 'failure'
    
    def _simulate_execution(self, tool_call: Dict[str, Any], tool_info: Dict[str, Any], execution_type: str) -> Dict[str, Any]:
        """统一的模拟执行方法"""
        try:
            # 构建工具调用信息
            tool_call_text = json.dumps(tool_call, ensure_ascii=False, indent=2)
            examples_text = json.dumps(tool_info.get('examples', []), ensure_ascii=False, indent=2)
            
            
            # 构建提示词
            prompt = self.prompts.EXECUTION_RESULT_TEMPLATE.format(
                tool_call=tool_call_text,
                examples=examples_text,
                execution_type=execution_type,
                current_state=json.dumps(self.execution_state, ensure_ascii=False, indent=2)
            )
            
            # 调用LLM生成结果
            response = self.llm_client.generate_completion(
                prompt=prompt,
                system_prompt=self.prompts.TOOL_EXECUTION_SYSTEM,
            )            
            # 解析LLM响应
            try:
                result = self.llm_client.parse_json_response(response)
            except Exception as parse_error:
                self.logger.warning(f"Failed to parse LLM response: {parse_error}")
                return self._create_default_result(tool_name, parameters, execution_type)
            
            # 确保结果格式正确
            if 'status' not in result:
                result['status'] = execution_type if execution_type != 'partial_success' else 'success'
            if 'metadata' not in result:
                result['metadata'] = {}
            
            tool_name = tool_info.get('name', 'unknown')
            result['metadata'].update({
                'tool_name': tool_name,
                'timestamp': datetime.now().isoformat(),
                'execution_time': result.get('metadata', {}).get('execution_time', round(random.uniform(0.1, 2.0), 2)),
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to simulate execution: {e}")
            tool_name = tool_call.get('name', 'unknown')
            parameters = tool_call.get('arguments', {})
            return self._create_default_result(tool_name, parameters, execution_type)
    
    def _create_error_result(self, tool_name: str, error_message: str, error_type: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            "status": "failure",
            "result": None,
            "message": error_message,
            "metadata": {
                "tool_name": tool_name,
                "timestamp": datetime.now().isoformat(),
                "error_type": error_type,
                "execution_time": 0.0
            }
        }
    
    def _create_default_result(self, tool_name: str, parameters: Dict[str, Any], execution_type: str) -> Dict[str, Any]:
        """创建默认结果"""
        if execution_type == 'success':
            return {
                "status": "success",
                "result": f"Tool {tool_name} executed successfully with parameters: {parameters}",
                "message": "Operation completed successfully",
                "metadata": {
                    "tool_name": tool_name,
                    "timestamp": datetime.now().isoformat(),
                    "execution_time": round(random.uniform(0.1, 2.0), 2),
                    "execution_type": execution_type
                }
            }
        elif execution_type == 'partial_success':
            return {
                "status": "success",
                "result": f"Tool {tool_name} executed with partial success",
                "message": "Operation completed with warnings",
                "metadata": {
                    "tool_name": tool_name,
                    "timestamp": datetime.now().isoformat(),
                    "execution_time": round(random.uniform(0.1, 2.0), 2),
                    "execution_type": execution_type,
                    "warnings": ["Some optional parameters were missing or invalid"]
                }
            }
        else:  # failure
            return {
                "status": "failure",
                "result": None,
                "message": f"Tool {tool_name} execution failed",
                "metadata": {
                    "tool_name": tool_name,
                    "timestamp": datetime.now().isoformat(),
                    "execution_time": 0.0,
                    "execution_type": execution_type,
                    "error_type": "execution_error"
                }
            }
    
    def _update_execution_state(self, tool_name: str, parameters: Dict[str, Any], result: Dict[str, Any]):
        """更新执行状态"""
        try:
            # 记录执行历史
            if 'execution_history' not in self.execution_state:
                self.execution_state['execution_history'] = []
            
            execution_record = {
                'tool_name': tool_name,
                'parameters': parameters,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            
            self.execution_state['execution_history'].append(execution_record)

        except Exception as e:
            self.logger.error(f"Failed to update execution state: {e}")    

    def register_tools(self, tools_info: Dict[str, Any]):
        """注册工具信息"""
        self.tools_registry.update(tools_info)
        self.logger.info(f"Registered {len(tools_info)} tools")