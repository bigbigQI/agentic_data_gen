"""
任务生成模块
负责为智能体生成多轮对话任务和评分标准
"""

import logging
from typing import Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.base_module import BaseModule
from core.models import Task, AgentConfig, DifficultyLevel
from core.exceptions import AgentDataGenException
from .task_designer import TaskDesigner


class TaskGenerator(BaseModule):
    """任务生成模块主类"""
    
    def __init__(self, config: Dict[str, Any] = None, logger: logging.Logger = None):
        """
        初始化任务生成模块
        
        Args:
            config: 配置字典
            logger: 日志器
        """
        super().__init__(config, logger)
        self.task_designer = None
        
        # 从配置中获取参数
        self.tasks_per_difficulty = 3  # 每个难度级别生成的任务数
        self.max_workers = 32  # 并发数
        
    def _setup(self):
        """设置模块组件"""
        # 更新配置
        config = self.config or {}
        self.tasks_per_difficulty = config.get('tasks_per_difficulty', 3)
        self.max_workers = config.get('max_workers', 32)
        
        self.task_designer = TaskDesigner(self.config, self.logger)
        self.task_designer.initialize()
        
    def process(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        处理任务生成
        
        Args:
            input_data: 包含智能体和工具信息的输入数据
            **kwargs: 其他参数
            
        Returns:
            生成的任务数据
        """
        try:
            agents = input_data.get('agents', [])
            tools_data = input_data.get('tools_data', {})
            
            if not agents:
                raise ValueError("No agents provided for task generation")
            
            if not tools_data:
                raise ValueError("No tools data provided for task generation")
            
            # 计算总任务数
            total_expected_tasks = len(agents) * len(DifficultyLevel) * self.tasks_per_difficulty
            self.logger.info(f"Starting task generation for {len(agents)} agents")
            self.logger.info(f"Expected total tasks: {total_expected_tasks}")
            
            # 生成所有任务参数组合
            task_params = self._generate_task_parameters(agents, tools_data)
            
            # 使用多线程并发生成所有任务
            all_tasks = self._generate_tasks_concurrently(task_params)
            
            # 保存任务批次
            if all_tasks:
                self.task_designer.save_batch_tasks(all_tasks)
            
            self.logger.info(f"Successfully generated {len(all_tasks)} tasks for {len(agents)} agents")
            
            return {
                'tasks': all_tasks,
                'total_tasks': len(all_tasks),
                'total_agents': len(agents),
                'generation_summary': {
                    'tasks_per_agent': len(all_tasks) / len(agents) if agents else 0,
                    'difficulty_distribution': self._calculate_difficulty_distribution(all_tasks),
                    'success_rate': len(all_tasks) / total_expected_tasks if total_expected_tasks > 0 else 0
                }
            }
            
        except Exception as e:
            self.logger.error(f"Task generation failed: {e}")
            raise AgentDataGenException(f"Failed to generate tasks: {e}")
    
    def _generate_task_parameters(self, agents: List[Dict[str, Any]], 
                                 tools_data: Dict[str, Any]) -> List[Tuple[str, List[str], DifficultyLevel, int]]:
        """
        生成所有任务参数组合
        
        Args:
            agents: 智能体列表
            tools_data: 工具数据
            
        Returns:
            任务参数列表: [(agent_id, agent_tools, difficulty, task_index), ...]
        """
        task_params = []
        
        for agent in agents:
            if isinstance(agent, dict):
                agent_id = agent.get('id')
                agent_tools = agent.get('tools', [])
            else:
                agent_id = agent.id
                agent_tools = agent.tools
            
            # 获取智能体的工具详细信息
            tools_info = self.task_designer._get_tools_info(agent_tools, tools_data)
            
            # 如果没有有效工具，跳过该智能体
            if not tools_info:
                self.logger.warning(f"No valid tools found for agent {agent_id}, skipping")
                continue
            
            # 为每个难度级别生成多个任务参数
            for difficulty in DifficultyLevel:
                for task_index in range(self.tasks_per_difficulty):
                    task_params.append((agent_id, tools_info, difficulty, task_index))
        
        return task_params
    
    def _generate_tasks_concurrently(self, task_params: List[Tuple[str, List[Dict[str, Any]], DifficultyLevel, int]]) -> List[Task]:
        """
        并发生成所有任务
        
        Args:
            task_params: 任务参数列表
            
        Returns:
            生成的任务列表
        """
        all_tasks = []
        failed_count = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_params = {}
            for params in task_params:
                agent_id, tools_info, difficulty, task_index = params
                future = executor.submit(
                    self.task_designer.generate_single_task,
                    agent_id=agent_id,
                    tools_info=tools_info,
                    difficulty=difficulty
                )
                future_to_params[future] = params
            
            # 收集结果
            for future in as_completed(future_to_params):
                params = future_to_params[future]
                agent_id, tools_info, difficulty, task_index = params
                
                try:
                    task = future.result()
                    if task:
                        all_tasks.append(task)
                        if len(all_tasks) % 50 == 0:  # 每50个任务输出进度
                            self.logger.info(f"Generated {len(all_tasks)} tasks so far...")
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    failed_count += 1
                    self.logger.error(f"Failed to generate task for agent {agent_id}, difficulty {difficulty.value}: {e}")
        
        if failed_count > 0:
            self.logger.warning(f"Failed to generate {failed_count} tasks out of {len(task_params)} total")
        
        return all_tasks
    
    def _calculate_difficulty_distribution(self, tasks: List[Task]) -> Dict[str, int]:
        """计算任务难度分布"""
        distribution = {'simple': 0, 'medium': 0, 'complex': 0}
        
        for task in tasks:
            difficulty = task.difficulty.value if hasattr(task.difficulty, 'value') else task.difficulty
            if difficulty in distribution:
                distribution[difficulty] += 1
        
        return distribution
