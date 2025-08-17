"""
任务生成模块
负责为智能体生成多轮对话任务和评分标准
"""


from .task_designer import TaskDesigner
from .task_generator import TaskGenerator

__all__ = ['TaskDesigner', 'TaskGenerator']
