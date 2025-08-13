"""
任务生成模块
负责为智能体生成多轮对话任务和评分标准
"""

import logging
from typing import Dict, Any, List
from core.base_module import BaseModule
from core.models import Task, AgentConfig, DifficultyLevel
from core.exceptions import AgentDataGenException
from .task_designer import TaskDesigner


class TaskGeneratorModule(BaseModule):
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
        
    def _setup(self):
        """设置模块组件"""
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
            
            self.logger.info(f"Starting task generation for {len(agents)} agents")
            
            # 为每个智能体生成任务
            all_tasks = []
            total_tasks = 0
            
            for agent in agents:
                if isinstance(agent, dict):
                    agent_id = agent.get('id')
                    agent_tools = agent.get('tools', [])
                else:
                    agent_id = agent.id
                    agent_tools = agent.tools
                
                self.logger.info(f"Generating tasks for agent {agent_id}")
                
                # 为每个难度级别生成任务
                agent_tasks = self.task_designer.process(
                    agent_id=agent_id,
                    agent_tools=agent_tools,
                    tools_data=tools_data,
                    **kwargs
                )
                
                all_tasks.extend(agent_tasks)
                total_tasks += len(agent_tasks)
                
                self.logger.info(f"Generated {len(agent_tasks)} tasks for agent {agent_id}")
            
            self.logger.info(f"Successfully generated {total_tasks} tasks for {len(agents)} agents")
            
            return {
                'tasks': all_tasks,
                'total_tasks': total_tasks,
                'total_agents': len(agents),
                'generation_summary': {
                    'tasks_per_agent': total_tasks / len(agents) if agents else 0,
                    'difficulty_distribution': self._calculate_difficulty_distribution(all_tasks)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Task generation failed: {e}")
            raise AgentDataGenException(f"Failed to generate tasks: {e}")
    
    def _calculate_difficulty_distribution(self, tasks: List[Task]) -> Dict[str, int]:
        """计算任务难度分布"""
        distribution = {'simple': 0, 'medium': 0, 'complex': 0}
        
        for task in tasks:
            difficulty = task.difficulty.value if hasattr(task.difficulty, 'value') else task.difficulty
            if difficulty in distribution:
                distribution[difficulty] += 1
        
        return distribution


__all__ = ['TaskGeneratorModule']
