#!/usr/bin/env python3
"""
任务生成脚本

为智能体批量生成多轮对话任务，包含详细的评分检查点
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
import random

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

from config.settings import settings
from utils.logger import setup_logger
from utils.file_manager import FileManager
from modules.task_generator import TaskGenerator


def setup_task_logger():
    """设置任务生成专用日志器"""
    logger = setup_logger(
        "task_generation",
        level=settings.LOGGING_CONFIG["level"],
        log_file=settings.LOGGING_CONFIG["file_path"]
    )
    return logger

def find_latest_agents_file() -> str:
    """查找最新的智能体文件"""
    data_path = Path('data/generated/agents')
    if not data_path.exists():
        raise FileNotFoundError("Agents data directory not found")
    
    # 优先查找agents_batch文件
    agents_files = list(data_path.glob('agents_batch_*.json'))
    
    if not agents_files:
        raise FileNotFoundError("No agents batch files found")
    
    # 返回最新的文件
    latest_file = max(agents_files, key=lambda f: f.stat().st_mtime)
    return str(latest_file)


def find_latest_tools_file() -> str:
    """查找最新的工具文件"""
    tools_dir = settings.get_data_path('tools')
    file_manager = FileManager(tools_dir)
    
    # 优先查找最终过滤后的工具文件
    final_files = file_manager.list_files(".", "*final_tools*.json")
    if final_files:
        latest_file = max(final_files, key=lambda f: file_manager.get_file_info(f)['modified'])
        return os.path.join(tools_dir, latest_file)
    
    return None


def load_agents_data(file_path: str) -> List[Dict[str, Any]]:
    """加载智能体数据"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and 'agents' in data:
        return data['agents']
    else:
        raise ValueError("Invalid agents data format")


def load_tools_data(file_path: str) -> Dict[str, Any]:
    """加载工具数据"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, list):
        # 转换为字典格式 {tool_id: tool_data}
        return {tool['id']: tool for tool in data}
    elif isinstance(data, dict):
        return data
    else:
        raise ValueError("Invalid tools data format")


def validate_agent_tools(agents: List[Dict[str, Any]], tools_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """验证智能体工具的有效性"""
    valid_agents = []
    
    for agent in agents:
        agent_tools = agent.get('tools', [])
        valid_tools = []
        
        for tool_id in agent_tools:
            if tool_id in tools_data:
                valid_tools.append(tool_id)
            else:
                print(f"Warning: Tool {tool_id} not found for agent {agent.get('id')}")
        
        if len(valid_tools) >= 2:  # 至少需要2个工具才能生成多轮任务
            agent['tools'] = valid_tools
            valid_agents.append(agent)
        else:
            print(f"Warning: Agent {agent.get('id')} has insufficient valid tools ({len(valid_tools)})")
    
    return valid_agents


def main():
    """主函数"""
    # 设置日志
    logger = setup_task_logger()
    
    try:
        print("🎯 开始任务生成流程...")
        
        # 1. 查找数据文件
        print("📁 查找最新的数据文件...")
        agents_file = find_latest_agents_file()
        tools_file = find_latest_tools_file()
        
        print(f"智能体文件: {agents_file}")
        print(f"工具文件: {tools_file}")
        
        # 2. 加载数据
        print("📊 加载数据...")
        agents_data = load_agents_data(agents_file)
        tools_data = load_tools_data(tools_file)
        
        print(f"加载了 {len(agents_data)} 个智能体")
        print(f"加载了 {len(tools_data)} 个工具")
        
        # 3. 验证数据
        print("✅ 验证智能体工具有效性...")
        valid_agents = validate_agent_tools(agents_data, tools_data)
        print(f"有效智能体数量: {len(valid_agents)}")
        
        if not valid_agents:
            print("❌ 没有找到有效的智能体，无法生成任务")
            return
        
        random.shuffle(valid_agents)
        # 5. 配置任务生成

        valid_agents = valid_agents[:2000]
        task_config = settings.GENERATION_CONFIG.get('tasks', {})
        
        # 6. 初始化任务生成模块
        print("🚀 初始化任务生成模块...")
        task_generator = TaskGenerator(config=task_config, logger=logger)
        task_generator.initialize()
        
        # 7. 生成任务
        print("🎨 开始生成任务...")
        result = task_generator.process({
            'agents': valid_agents,
            'tools_data': tools_data
        })
        
        # 8. 显示结果
        total_tasks = result['total_tasks']
        total_agents = result['total_agents']
        
        print(f"\\n✅ 任务生成完成！")
        print(f"处理智能体数量: {total_agents}")
        print(f"生成任务总数: {total_tasks}")
        
        # 显示难度分布和成功率
        difficulty_dist = result['generation_summary']['difficulty_distribution']
        success_rate = result['generation_summary']['success_rate']
        
        print(f"\\n📊 任务难度分布:")
        for difficulty, count in difficulty_dist.items():
            print(f"  {difficulty}: {count} 个任务")
        
        print(f"\\n📈 生成成功率: {success_rate:.2%}")
        print(f"\\n💾 任务数据已保存到 data/generated/tasks/ 目录")
        
    except FileNotFoundError as e:
        print(f"❌ 文件未找到: {e}")
        print("请确保已经生成了智能体和工具数据")
    except Exception as e:
        print(f"❌ 任务生成失败: {e}")
        logger.error(f"Task generation failed: {e}")
        raise


if __name__ == "__main__":
    main()
