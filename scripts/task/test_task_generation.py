#!/usr/bin/env python3
"""
任务生成模块测试脚本
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import json
from modules.task_generator.task_designer import TaskDesigner
from core.models import DifficultyLevel

def test_task_generation():
    """测试任务生成功能"""
    print("🧪 开始测试任务生成模块...")
    
    # 创建测试数据
    test_agent_id = "test_agent_001"
    
    # 模拟工具数据
    test_tools_info = [
        {
            'id': 'tool_weather',
            'name': 'get_weather',
            'description': '查询指定城市的当前天气信息',
            'parameters': [
                {
                    'name': 'city',
                    'type': 'string',
                    'description': '要查询天气的城市名称',
                    'required': True
                },
                {
                    'name': 'unit',
                    'type': 'string',
                    'description': '温度单位',
                    'required': False,
                    'enum': ['celsius', 'fahrenheit']
                }
            ]
        },
        {
            'id': 'tool_travel',
            'name': 'plan_travel',
            'description': '根据天气情况制定出行计划',
            'parameters': [
                {
                    'name': 'destination',
                    'type': 'string',
                    'description': '目的地',
                    'required': True
                },
                {
                    'name': 'weather_condition',
                    'type': 'string',
                    'description': '天气状况',
                    'required': True
                }
            ]
        },
        {
            'id': 'tool_reminder',
            'name': 'set_reminder',
            'description': '设置提醒事项',
            'parameters': [
                {
                    'name': 'message',
                    'type': 'string',
                    'description': '提醒内容',
                    'required': True
                },
                {
                    'name': 'time',
                    'type': 'string',
                    'description': '提醒时间',
                    'required': True
                }
            ]
        }
    ]
    
    try:
        # 初始化任务设计器
        task_designer = TaskDesigner()
        task_designer.initialize()
        
        print("✅ 任务设计器初始化成功")
        
        # 测试单个任务生成
        print("🎯 测试生成简单难度任务...")
        task = task_designer._generate_single_task(
            agent_id=test_agent_id,
            tools_info=test_tools_info,
            difficulty=DifficultyLevel.SIMPLE
        )
        
        if task:
            print("✅ 任务生成成功！")
            print(f"任务标题: {task.title}")
            print(f"任务难度: {task.difficulty.value}")
            print(f"期望工具: {task.expected_tools}")
            print(f"检查点数量: {len(task.rubric.checkpoints)}")
            print(f"检查点: {task.rubric.checkpoints}")
            print(f"任务描述长度: {len(task.description)} 字符")
            
            # 显示任务描述的前200个字符
            description_preview = task.description[:200] + "..." if len(task.description) > 200 else task.description
            print(f"任务描述预览: {description_preview}")
            
        else:
            print("❌ 任务生成失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_task_generation()
