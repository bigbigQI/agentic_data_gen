"""
测试多智能体交互功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
import logging
from datetime import datetime

from config.settings import settings
from utils.logger import setup_logger
from core.models import Task, AgentConfig, TaskRubric, DifficultyLevel, TaskType
from modules.interaction_coordinator import InteractionCoordinator


def setup_test_environment():
    """设置测试环境"""
    logger = setup_logger(
        "test_multi_agent",
        level="INFO",
        log_file=settings.ROOT_DIR / "logs" / "test_multi_agent.log"
    )
    
    logger.info("=" * 60)
    logger.info("多智能体交互功能测试")
    logger.info("=" * 60)
    
    return logger


def load_test_task():
    """从生成的数据文件中加载测试任务"""
    task_file = "/Users/larkz/Documents/apps/agent_data_gen/data/generated/tasks/tasks_agent_04c30284_20250811_163638.json"
    
    with open(task_file, 'r', encoding='utf-8') as f:
        tasks_data = json.load(f)
    
    if not tasks_data:
        raise ValueError("任务数据文件为空")
    
    # 选择第一个任务作为测试用例
    task_data = tasks_data[0]
    
    # 转换为Task对象
    rubric = TaskRubric(
        success_criteria=task_data['rubric']['success_criteria'],
        tool_usage_expectations=task_data['rubric']['tool_usage_expectations'],
        checkpoints=task_data['rubric']['checkpoints']
    )
    
    # 映射difficulty和task_type
    difficulty_map = {
        'simple': DifficultyLevel.SIMPLE,
        'medium': DifficultyLevel.MEDIUM,
        'complex': DifficultyLevel.COMPLEX
    }
    
    task_type_map = {
        'multi_turn': TaskType.MULTI_TURN,
        'single_turn': TaskType.SINGLE_TURN
    }
    
    task = Task(
        id=task_data['id'],
        agent_id=task_data['agent_id'],
        title=task_data['title'],
        description=task_data['description'],
        difficulty=difficulty_map.get(task_data['difficulty'], DifficultyLevel.MEDIUM),
        task_type=task_type_map.get(task_data['task_type'], TaskType.MULTI_TURN),
        expected_tools=task_data['expected_tools'],
        rubric=rubric,
        context=task_data['context']
    )
    
    return task, task_file


def load_test_agent(target_agent_id=None):
    """从生成的数据文件中加载测试智能体"""
    agent_file = "/Users/larkz/Documents/apps/agent_data_gen/data/generated/agents/agents_batch_20250811_135039.json"
    
    with open(agent_file, 'r', encoding='utf-8') as f:
        agents_data = json.load(f)
    
    if not agents_data:
        raise ValueError("智能体数据文件为空")
    
    # 如果指定了agent_id，查找对应的智能体
    if target_agent_id:
        agent_data = next((agent for agent in agents_data if agent['id'] == target_agent_id), None)
        if not agent_data:
            # 如果找不到指定的智能体，使用第一个
            agent_data = agents_data[0]
    else:
        # 选择第一个智能体作为测试用例
        agent_data = agents_data[0]
    
    # 转换为AgentConfig对象
    agent_config = AgentConfig(
        id=agent_data['id'],
        system_prompt=agent_data['system_prompt'],
        tools=agent_data['tools']
    )
    
    return agent_config, agent_file


def load_test_tools(agent_tools=None):
    """从生成的数据文件中加载测试工具"""
    tool_file = "/Users/larkz/Documents/apps/agent_data_gen/data/generated/tools/final_tools_20250810_171024.json"
    
    with open(tool_file, 'r', encoding='utf-8') as f:
        tools_data = json.load(f)
    
    if not tools_data:
        raise ValueError("工具数据文件为空")
    
    # 如果指定了agent_tools，只加载相关的工具
    if agent_tools:
        # 根据工具ID过滤工具
        filtered_tools = {}
        for tool in tools_data:
            if tool['id'] in agent_tools:
                filtered_tools[tool['name']] = tool
        
        # 如果找不到匹配的工具，随机选择几个工具
        if not filtered_tools:
            print("没有找到匹配的工具")
            return None, None
    else:
        # 选择前几个工具作为测试用例
        print("没有指定工具")
        return None, None
    
    return filtered_tools, tool_file


def test_unified_session_interaction(logger):
    """测试统一会话管理的多智能体交互"""
    logger.info("\n测试统一会话管理的多智能体交互...")
    
    try:
        # 创建交互协调器
        coordinator = InteractionCoordinator(logger=logger)
        coordinator.initialize()
        
        # 从生成的数据文件中加载测试数据
        logger.info("正在加载生成的测试数据...")
        
        # 加载任务
        task, task_file = load_test_task()
        logger.info(f"已加载任务: {task.title} (来自文件: {task_file})")
        
        # 加载对应的智能体（尝试匹配agent_id）
        agent_config, agent_file = load_test_agent(task.agent_id)
        logger.info(f"已加载智能体: {agent_config.id} (来自文件: {agent_file})")
        
        # 加载工具（根据智能体的工具列表）
        tools_info, tool_file = load_test_tools(agent_config.tools)
        logger.info(f"已加载 {len(tools_info)} 个工具 (来自文件: {tool_file})")

        # 显示加载的数据信息
        logger.info(f"任务详情:")
        logger.info(f"  - 标题: {task.title}")
        logger.info(f"  - 难度: {task.difficulty.value}")
        logger.info(f"  - 类型: {task.task_type.value}")
        logger.info(f"  - 期望工具: {task.expected_tools}")
        logger.info(f"实际加载工具: {list(tools_info.keys())}")
         
        # 执行单个交互
        trajectory = coordinator.execute_single_interaction(task, agent_config, tools_info)
        
        logger.info(f"生成交互轨迹: {trajectory.id}")
        logger.info(f"对话轮数: {len(trajectory.session.turns)}")
        
        # 输出前几轮对话示例
        for i, turn in enumerate(trajectory.session.turns[:6]):
            speaker = "用户" if turn.speaker == "user" else ("智能体" if turn.speaker == "agent" else "工具执行")
            message = turn.message
            if isinstance(message, list):
                # 工具执行结果
                message_str = "; ".join([f"{r.get('tool_name', 'tool')}: {r.get('status', 'unknown')}" for r in message])
            else:
                message_str = str(message)[:100]
            logger.info(f"第{i+1}轮 - {speaker}: {message_str}...")
        
        # 获取协调器统计
        stats = coordinator.get_coordinator_stats()
        logger.info(f"协调器统计: {json.dumps(stats, ensure_ascii=False, indent=2)}")
        
        logger.info("✅ 统一会话管理的多智能体交互测试成功")
        return True
        
    except Exception as e:
        logger.error(f"❌ 统一会话管理的多智能体交互测试失败: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return False


def main():
    """主测试函数"""
    try:
        # 设置测试环境
        logger = setup_test_environment()
        
        # 运行测试
        test_result = test_unified_session_interaction(logger)
        
        # 统计测试结果
        logger.info("\n" + "=" * 60)
        logger.info("测试结果汇总")
        logger.info("=" * 60)
        logger.info(f"统一会话管理测试: {'通过' if test_result else '失败'}")
        
        if test_result:
            logger.info("🎉 统一会话管理多智能体交互测试通过！")
        else:
            logger.warning("⚠️ 测试失败，请检查相关模块")
        
        return test_result
        
    except Exception as e:
        print(f"测试执行失败: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)