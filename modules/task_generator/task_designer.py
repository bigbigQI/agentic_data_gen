"""
任务设计器
负责为智能体设计多轮对话任务和对应的评分标准
"""

import json
import random
from typing import Dict, Any, List, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from core.base_module import BaseModule
from core.models import Task, TaskRubric, DifficultyLevel, TaskType
from core.exceptions import AgentDataGenException
from utils.llm_client import LLMClient
from utils.data_processor import DataProcessor
from utils.file_manager import FileManager


class TaskDesigner(BaseModule):
    """任务设计器"""
    
    def __init__(self, config: Dict[str, Any] = None, logger: logging.Logger = None):
        """
        初始化任务设计器
        
        Args:
            config: 配置字典
            logger: 日志器
        """
        super().__init__(config, logger)
        
        self.llm_client = None
        self.data_processor = None
        self.file_manager = None
        
        # 默认配置
        self.tasks_per_difficulty = 2  # 每个难度级别生成的任务数
        self.max_workers = 3  # 并发数
        
    def _setup(self):
        """设置组件"""
        from config.settings import settings
        
        llm_config = settings.get_llm_config()
        llm_config['provider'] = settings.DEFAULT_LLM_PROVIDER
        self.llm_client = LLMClient(llm_config, self.logger)
        
        # 初始化数据处理器
        self.data_processor = DataProcessor(self.logger)
        
        # 初始化文件管理器
        data_path = settings.get_data_path('tasks')
        self.file_manager = FileManager(data_path, self.logger)
        
        # 更新配置
        config = self.config or {}
        self.tasks_per_difficulty = config.get('tasks_per_difficulty', 2)
        self.max_workers = config.get('max_workers', 3)
    
    def process(self, agent_id: str, agent_tools: List[str], 
                               tools_data: Dict[str, Any], **kwargs) -> List[Task]:
        """
        为指定智能体生成任务
        
        Args:
            agent_id: 智能体ID
            agent_tools: 智能体可用的工具列表
            tools_data: 工具详细信息
            **kwargs: 其他参数
            
        Returns:
            生成的任务列表
        """
        try:
            # 获取工具详细信息
            available_tools_info = self._get_tools_info(agent_tools, tools_data)
            
            if not available_tools_info:
                self.logger.warning(f"No valid tools found for agent {agent_id}")
                return []
            
            # 并发生成不同难度的任务
            all_tasks = []
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_difficulty = {}
                
                for difficulty in DifficultyLevel:
                    future = executor.submit(
                        self._generate_tasks_for_difficulty,
                        agent_id,
                        available_tools_info,
                        difficulty,
                        self.tasks_per_difficulty
                    )
                    future_to_difficulty[future] = difficulty
                
                # 收集结果
                for future in as_completed(future_to_difficulty):
                    difficulty = future_to_difficulty[future]
                    try:
                        tasks = future.result()
                        all_tasks.extend(tasks)
                        self.logger.debug(f"Generated {len(tasks)} {difficulty.value} tasks for agent {agent_id}")
                    except Exception as e:
                        self.logger.error(f"Failed to generate {difficulty.value} tasks for agent {agent_id}: {e}")
            
            # 保存任务
            if all_tasks:
                self._save_agent_tasks(agent_id, all_tasks)
            
            return all_tasks
            
        except Exception as e:
            self.logger.error(f"Failed to generate tasks for agent {agent_id}: {e}")
            return []
    
    def _generate_tasks_for_difficulty(self, agent_id: str, tools_info: List[Dict[str, Any]], 
                                     difficulty: DifficultyLevel, count: int) -> List[Task]:
        """为指定难度生成任务"""
        tasks = []
        
        for i in range(count):
            try:
                task = self._generate_single_task(agent_id, tools_info, difficulty)
                if task:
                    tasks.append(task)
            except Exception as e:
                self.logger.error(f"Failed to generate task {i+1} for difficulty {difficulty.value}: {e}")
                continue
        
        return tasks
    
    def _generate_single_task(self, agent_id: str, tools_info: List[Dict[str, Any]], 
                            difficulty: DifficultyLevel) -> Optional[Task]:
        """生成单个任务"""
        try:
            from config.prompts.task_prompts import TaskPrompts
            
            # 准备工具信息
            tools_details = self._format_tools_for_prompt(tools_info)
            available_tools = [tool['name'] for tool in tools_info]
            
            # 构建提示词
            prompts = TaskPrompts()
            prompt = prompts.TASK_GENERATION.format(
                available_tools=available_tools,
                tools_details=tools_details,
                difficulty=difficulty.value
            )
            
            # 调用LLM生成任务
            response = self.llm_client.generate_completion(prompt=prompt)
            task_data = self.llm_client.parse_json_response(response)
            
            if not task_data:
                self.logger.error("Failed to parse task generation response")
                return None
            
            # 验证任务
            if not self._validate_task_data(task_data, available_tools):
                self.logger.warning("Generated task failed validation")
                return None
            
            # 创建Task对象
            task = self._create_task_from_data(agent_id, task_data, difficulty)
            
            return task
            
        except Exception as e:
            self.logger.error(f"Failed to generate single task: {e}")
            return None
    
    def _get_tools_info(self, tool_ids: List[str], tools_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取工具详细信息"""
        tools_info = []
        
        for tool_id in tool_ids:
            if tool_id in tools_data:
                tools_info.append(tools_data[tool_id])
            else:
                self.logger.warning(f"Tool {tool_id} not found in tools_data")
        
        return tools_info
    
    def _format_tools_for_prompt(self, tools_info: List[Dict[str, Any]]) -> str:
        """格式化工具信息用于提示词"""
        tool_descriptions = []
        
        for tool in tools_info:
            tool_name = tool.get('name', '')
            tool_desc = tool.get('description', '')
            parameters = tool.get('parameters', [])
            
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
            tool_text = f"**{tool_name}**\\n功能：{tool_desc}"
            if param_list:
                tool_text += "\\n参数：\\n" + "\\n".join(param_list)
            
            tool_descriptions.append(tool_text)
        
        return "\\n\\n".join(tool_descriptions)
    
    def _validate_task_data(self, task_data: Dict[str, Any], available_tools: List[str]) -> bool:
        """验证生成的任务数据"""
        try:
            # 检查基本结构
            if 'task' not in task_data or 'rubric' not in task_data:
                return False
            
            task_info = task_data['task']
            rubric_info = task_data['rubric']
            
            # 检查任务基本字段
            required_task_fields = ['title', 'description', 'difficulty']
            for field in required_task_fields:
                if field not in task_info:
                    return False
            
            # 检查评分标准字段
            required_rubric_fields = ['checkpoints', 'success_criteria']
            for field in required_rubric_fields:
                if field not in rubric_info:
                    return False
            
            # 检查检查点是否使用了可用的工具
            checkpoints = rubric_info.get('checkpoints', [])
            if not checkpoints:
                return False
            
            # 提取检查点中的工具名称并验证
            used_tools = []
            for checkpoint in checkpoints:
                # 从 "tool_name()" 格式中提取工具名称
                if '(' in checkpoint:
                    tool_name = checkpoint.split('(')[0].strip()
                    used_tools.append(tool_name)
            
            # 检查是否所有使用的工具都在可用工具列表中
            for tool in used_tools:
                if tool not in available_tools:
                    self.logger.warning(f"Tool {tool} in checkpoints not available in agent tools")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Task validation error: {e}")
            return False
    
    def _create_task_from_data(self, agent_id: str, task_data: Dict[str, Any], 
                             difficulty: DifficultyLevel) -> Task:
        """从数据创建Task对象"""
        task_info = task_data['task']
        rubric_info = task_data['rubric']
        
        # 生成任务ID
        task_id = self.data_processor.generate_id('task', {
            'agent_id': agent_id,
            'title': task_info.get('title', ''),
            'difficulty': difficulty.value
        })
        
        # 提取期望使用的工具
        checkpoints = rubric_info.get('checkpoints', [])
        expected_tools = []
        for checkpoint in checkpoints:
            if '(' in checkpoint:
                tool_name = checkpoint.split('(')[0].strip()
                expected_tools.append(tool_name)
        
        # 创建TaskRubric
        rubric = TaskRubric(
            success_criteria=rubric_info.get('success_criteria', []),
            tool_usage_expectations=rubric_info.get('tool_usage_expectations', []),
            checkpoints=checkpoints
        )
        
        # 创建Task
        task = Task(
            id=task_id,
            agent_id=agent_id,
            title=task_info.get('title', ''),
            description=task_info.get('description', ''),
            difficulty=difficulty,
            task_type=TaskType.MULTI_TURN,
            expected_tools=expected_tools,
            rubric=rubric,
            context=task_info.get('user_context', {}),
            metadata={
                'expected_turns': task_info.get('expected_turns', '4-8'),
                'generated_at': datetime.now().isoformat()
            }
        )
        
        return task
    
    def _save_agent_tasks(self, agent_id: str, tasks: List[Task]):
        """保存智能体的任务"""
        try:
            # 转换为可序列化的格式
            tasks_data = []
            for task in tasks:
                task_dict = {
                    'id': task.id,
                    'agent_id': task.agent_id,
                    'title': task.title,
                    'description': task.description,
                    'difficulty': task.difficulty.value,
                    'task_type': task.task_type.value,
                    'expected_tools': task.expected_tools,
                    'rubric': {
                        'success_criteria': task.rubric.success_criteria,
                        'tool_usage_expectations': task.rubric.tool_usage_expectations,
                        'checkpoints': task.rubric.checkpoints
                    },
                    'context': task.context,
                    'metadata': task.metadata,
                    'created_at': task.created_at.isoformat()
                }
                tasks_data.append(task_dict)
            
            # 保存文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tasks_{agent_id}_{timestamp}.json"
            
            self.file_manager.save_json(tasks_data, filename)
            self.logger.info(f"Saved {len(tasks)} tasks for agent {agent_id} to {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to save tasks for agent {agent_id}: {e}")
            raise AgentDataGenException(f"Failed to save agent tasks: {e}")
    
    def save_batch_tasks(self, tasks: List[Task]):
        """批量保存任务"""
        try:
            # 转换为可序列化的格式
            tasks_data = []
            for task in tasks:
                task_dict = {
                    'id': task.id,
                    'agent_id': task.agent_id,
                    'title': task.title,
                    'description': task.description,
                    'difficulty': task.difficulty.value,
                    'task_type': task.task_type.value,
                    'expected_tools': task.expected_tools,
                    'rubric': {
                        'success_criteria': task.rubric.success_criteria,
                        'tool_usage_expectations': task.rubric.tool_usage_expectations,
                        'checkpoints': task.rubric.checkpoints
                    },
                    'context': task.context,
                    'metadata': task.metadata,
                    'created_at': task.created_at.isoformat()
                }
                tasks_data.append(task_dict)
            
            # 保存文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tasks_batch_{timestamp}.json"
            
            self.file_manager.save_json(tasks_data, filename)
            self.logger.info(f"Saved {len(tasks)} tasks to {filename}")
            
            return filename
            
        except Exception as e:
            self.logger.error(f"Failed to save batch tasks: {e}")
            raise AgentDataGenException(f"Failed to save batch tasks: {e}")
