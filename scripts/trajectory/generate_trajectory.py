#!/usr/bin/env python3
"""
轨迹生成脚本

基于已生成的任务、智能体和工具数据，生成多智能体交互轨迹
"""

import os
import sys
import json
import random
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from utils.logger import setup_logger
from utils.file_manager import FileManager
from core.models import Task, AgentConfig, TaskRubric, DifficultyLevel, TaskType
from modules.interaction_coordinator import InteractionCoordinator


def setup_trajectory_logger():
    """设置轨迹生成专用日志器"""
    logger = setup_logger(
        "trajectory_generation",
        level=settings.LOGGING_CONFIG["level"],
        log_file=settings.LOGGING_CONFIG["file_path"]
    )
    return logger


def validate_environment():
    """验证环境配置"""
    required_keys = ['OPENAI_API_KEY']
    missing_keys = []
    
    for key in required_keys:
        if not os.getenv(key):
            missing_keys.append(key)
    
    if missing_keys:
        print(f"❌ 缺少环境变量: {', '.join(missing_keys)}")
        print("请确保在 .env 文件中设置以下变量:")
        for key in missing_keys:
            print(f"  {key}=your_api_key_here")
        return False
    
    print("✅ 环境变量检查通过")
    return True


def find_latest_tasks_file() -> Optional[str]:
    """查找最新的任务文件"""
    tasks_dir = settings.get_data_path('tasks')
    file_manager = FileManager(tasks_dir)
    
    # 查找批量任务文件
    batch_files = file_manager.list_files(".", "*tasks_batch*.json")
    if batch_files:
        latest_file = max(batch_files, key=lambda f: file_manager.get_file_info(f)['modified'])
        return os.path.join(tasks_dir, latest_file)
    
    return None


def find_latest_agents_file() -> Optional[str]:
    """查找最新的智能体文件"""
    agents_dir = settings.get_data_path('agents')
    
    if not agents_dir.exists():
        return None
    
    # 优先查找agents_batch文件
    agents_files = list(agents_dir.glob('agents_batch_*.json'))
    
    if agents_files:
        latest_file = max(agents_files, key=lambda f: f.stat().st_mtime)
        return str(latest_file)
    
    return None


def find_latest_tools_file() -> Optional[str]:
    """查找最新的工具文件"""
    tools_dir = settings.get_data_path('tools')
    file_manager = FileManager(tools_dir)
    
    # 优先查找最终过滤后的工具文件
    final_files = file_manager.list_files(".", "*final_tools*.json")
    if final_files:
        latest_file = max(final_files, key=lambda f: file_manager.get_file_info(f)['modified'])
        return os.path.join(tools_dir, latest_file)
    
    return None


def load_tasks_data(file_path: str) -> List[Dict[str, Any]]:
    """加载任务数据"""
    print(f"📂 加载任务数据: {os.path.basename(file_path)}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        tasks_data = json.load(f)
    
    if not isinstance(tasks_data, list):
        raise ValueError("Invalid tasks data format: expected list")
    
    print(f"✅ 成功加载 {len(tasks_data)} 个任务")
    return tasks_data


def load_agents_data(file_path: str) -> List[Dict[str, Any]]:
    """加载智能体数据"""
    print(f"📂 加载智能体数据: {os.path.basename(file_path)}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, list):
        agents_data = data
    elif isinstance(data, dict) and 'agents' in data:
        agents_data = data['agents']
    else:
        raise ValueError("Invalid agents data format")
    
    print(f"✅ 成功加载 {len(agents_data)} 个智能体")
    return agents_data


def load_tools_data(file_path: str) -> Dict[str, Any]:
    """加载工具数据"""
    print(f"📂 加载工具数据: {os.path.basename(file_path)}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, list):
        # 转换为字典格式 {tool_id: tool_data}
        tools_data = {tool['id']: tool for tool in data}
    elif isinstance(data, dict):
        tools_data = data
    else:
        raise ValueError("Invalid tools data format")
    
    print(f"✅ 成功加载 {len(tools_data)} 个工具")
    return tools_data


def convert_task_dict_to_object(task_data: Dict[str, Any]) -> Task:
    """将任务字典转换为Task对象"""
    # 转换TaskRubric
    rubric_data = task_data['rubric']
    rubric = TaskRubric(
        success_criteria=rubric_data['success_criteria'],
        tool_usage_expectations=rubric_data.get('tool_usage_expectations', []),
        checkpoints=rubric_data['checkpoints']
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
        metadata=task_data.get('metadata', {})
    )
    
    return task


def convert_agent_dict_to_object(agent_data: Dict[str, Any]) -> AgentConfig:
    """将智能体字典转换为AgentConfig对象"""
    return AgentConfig(
        id=agent_data['id'],
        system_prompt=agent_data['system_prompt'],
        tools=agent_data['tools']
    )


def load_existing_trajectory_task_ids(trajectory_dir: Path, logger: logging.Logger) -> set:
    """
    加载现有轨迹中的任务ID
    
    Args:
        trajectory_dir: 轨迹目录路径
        logger: 日志器
        
    Returns:
        已存在的任务ID集合
    """
    existing_task_ids = set()
    
    if not trajectory_dir.exists():
        logger.info(f"轨迹目录不存在: {trajectory_dir}")
        return existing_task_ids
    
    # 查找所有JSON文件
    json_files = list(trajectory_dir.glob("*.json"))
    logger.info(f"在 {trajectory_dir} 中找到 {len(json_files)} 个轨迹文件")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                trajectory_data = json.load(f)
            
            # 提取task_id
            task_id = trajectory_data.get('task_id')
            if task_id:
                existing_task_ids.add(task_id)
                logger.debug(f"发现已存在的任务ID: {task_id} (来自文件: {json_file.name})")
            
        except Exception as e:
            logger.warning(f"读取轨迹文件失败 {json_file.name}: {e}")
            continue
    
    logger.info(f"总共发现 {len(existing_task_ids)} 个已存在的任务ID")
    return existing_task_ids


def filter_existing_tasks(
    matched_pairs: List[Tuple[Task, AgentConfig, Dict[str, Any]]], 
    existing_task_ids: set,
    logger: logging.Logger
) -> List[Tuple[Task, AgentConfig, Dict[str, Any]]]:
    """
    过滤掉已经存在的任务
    
    Args:
        matched_pairs: 匹配的任务-智能体对列表
        existing_task_ids: 已存在的任务ID集合
        logger: 日志器
        
    Returns:
        过滤后的匹配对列表
    """
    if not existing_task_ids:
        logger.info("没有发现已存在的任务，不进行过滤")
        return matched_pairs
    
    filtered_pairs = []
    filtered_count = 0
    
    for task, agent, tools in matched_pairs:
        if task.id in existing_task_ids:
            logger.debug(f"过滤已存在的任务: {task.id}")
            filtered_count += 1
        else:
            filtered_pairs.append((task, agent, tools))
    
    logger.info(f"过滤掉 {filtered_count} 个已存在的任务，剩余 {len(filtered_pairs)} 个任务待生成")
    return filtered_pairs


def match_tasks_and_agents(tasks_data: List[Dict[str, Any]], 
                          agents_data: List[Dict[str, Any]], 
                          tools_data: Dict[str, Any]) -> List[Tuple[Task, AgentConfig, Dict[str, Any]]]:
    """匹配任务和智能体，并验证工具可用性"""
    matched_pairs = []
    agents_dict = {agent['id']: agent for agent in agents_data}
    
    print("🔗 匹配任务和智能体...")
    
    for task_data in tasks_data:
        agent_id = task_data['agent_id']
        
        # 查找对应的智能体
        if agent_id not in agents_dict:
            print(f"⚠️ 任务 {task_data['id']} 对应的智能体 {agent_id} 未找到，跳过")
            continue
        
        agent_data = agents_dict[agent_id]
        agent_tools = agent_data.get('tools', [])
        
        # 验证工具可用性
        available_tools = {}
        valid_tools_count = 0
        
        for tool_id in agent_tools:
            if tool_id in tools_data:
                available_tools[tools_data[tool_id]['name']] = tools_data[tool_id]
                valid_tools_count += 1
        
        if valid_tools_count < 2:  # 至少需要2个有效工具
            print(f"⚠️ 智能体 {agent_id} 的有效工具不足 ({valid_tools_count})，跳过")
            continue
        
        # 转换为对象
        task_obj = convert_task_dict_to_object(task_data)
        agent_obj = convert_agent_dict_to_object(agent_data)
        
        matched_pairs.append((task_obj, agent_obj, available_tools))
    
    print(f"✅ 成功匹配 {len(matched_pairs)} 个任务-智能体对")
    return matched_pairs


def generate_single_trajectory(logger: logging.Logger,
                             task: Task, 
                             agent_config: AgentConfig, 
                             tools_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """生成单个轨迹（每个线程使用独立的coordinator）"""
    try:
        # 为每个轨迹生成创建独立的协调器实例以避免并发问题
        trajectory_config = settings.GENERATION_CONFIG.get('trajectories', {})
        coordinator = InteractionCoordinator(config=trajectory_config, logger=logger)
        coordinator.initialize()
        
        trajectory = coordinator.execute_single_interaction(task, agent_config, tools_info)
        
        return {
            'trajectory_id': trajectory.id,
            'task_id': task.id,
            'agent_id': agent_config.id,
            'turns_count': len(trajectory.session.turns),
            'status': 'success'
        }
        
    except Exception as e:
        logger.error(f"生成轨迹失败 - 任务: {task.id}, 智能体: {agent_config.id}, 错误: {e}")
        return {
            'task_id': task.id,
            'agent_id': agent_config.id,
            'status': 'failed',
            'error': str(e)
        }


def main():
    """主函数"""
    print("🎯 轨迹生成器")
    print("="*60)
    
    # 验证环境
    if not validate_environment():
        return
    
    # 设置日志
    logger = setup_trajectory_logger()
    
    try:
        # 1. 查找数据文件
        print("📁 查找最新的数据文件...")
        
        tasks_file = find_latest_tasks_file()
        agents_file = find_latest_agents_file()
        tools_file = find_latest_tools_file()
        
        if not tasks_file:
            print("❌ 未找到任务数据文件")
            return
        if not agents_file:
            print("❌ 未找到智能体数据文件")
            return
        if not tools_file:
            print("❌ 未找到工具数据文件")
            return
        
        print(f"任务文件: {os.path.basename(tasks_file)}")
        print(f"智能体文件: {os.path.basename(agents_file)}")
        print(f"工具文件: {os.path.basename(tools_file)}")
        
        # 2. 加载数据
        print("\n📊 加载数据...")
        tasks_data = load_tasks_data(tasks_file)
        agents_data = load_agents_data(agents_file)
        tools_data = load_tools_data(tools_file)


        
        # 3. 匹配任务和智能体
        print("\n🔗 匹配数据...")
        matched_pairs = match_tasks_and_agents(tasks_data, agents_data, tools_data)
        
        # 4. 过滤已存在的任务
        print("\n🔍 检查并过滤已存在的任务...")
        trajectory_1_dir = settings.DATA_DIR / "generated" / "trajectories_1"
        existing_task_ids = load_existing_trajectory_task_ids(trajectory_1_dir, logger)
        
        if existing_task_ids:
            print(f"发现 {len(existing_task_ids)} 个已存在的任务，将进行过滤")
            matched_pairs = filter_existing_tasks(matched_pairs, existing_task_ids, logger)
        else:
            print("没有发现已存在的任务")
        
        if not matched_pairs:
            print("❌ 经过过滤后，没有找到待生成的任务-智能体匹配对")
            return
        
        # 5. 获取配置
        trajectory_config = settings.GENERATION_CONFIG.get('trajectories', {})
        max_trajectories = trajectory_config.get('max_count', 10)  # 限制生成数量
        max_workers = trajectory_config.get('max_workers', 8)
        
        # 随机选择匹配对（避免全部生成）
        if len(matched_pairs) > max_trajectories:
            print(f"🎲 随机选择 {max_trajectories} 个匹配对进行生成")
            matched_pairs = random.sample(matched_pairs, max_trajectories)
        
        print(f"\n🎯 生成配置:")
        print(f"  目标轨迹数量: {len(matched_pairs)}")
        print(f"  并发数: {max_workers}")

        # 6. 准备轨迹生成
        print("\n🔄 开始轨迹生成...")

        start_time = datetime.now()
        
        results = []
        successful_count = 0
        failed_count = 0
        
        # 使用多线程生成轨迹
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_params = {}
            
            for task, agent_config, tools_info in matched_pairs:
                future = executor.submit(
                    generate_single_trajectory,
                    logger,
                    task,
                    agent_config,
                    tools_info
                )
                future_to_params[future] = (task.id, agent_config.id)
            
            # 收集结果
            for i, future in enumerate(as_completed(future_to_params), 1):
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result['status'] == 'success':
                        successful_count += 1
                        if successful_count % 10 == 0:  # 每10个成功轨迹输出进度
                            print(f"✅ 已成功生成 {successful_count} 个轨迹...")
                    else:
                        failed_count += 1
                        
                    # 输出总进度
                    if i % 20 == 0:
                        print(f"📊 总进度: {i}/{len(matched_pairs)} ({i/len(matched_pairs)*100:.1f}%)")
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"轨迹生成任务异常: {e}")
        
        end_time = datetime.now()
        generation_time = (end_time - start_time).total_seconds()
        
        # 7. 输出统计结果
        print(f"\n✅ 轨迹生成完成！")
        print(f"📊 生成统计:")
        print(f"  成功生成: {successful_count} 个轨迹")
        print(f"  失败数量: {failed_count} 个")
        print(f"  成功率: {successful_count/(successful_count+failed_count)*100:.1f}%")
        print(f"  总耗时: {generation_time:.2f} 秒")
        
        if successful_count > 0:
            print(f"  生成速度: {successful_count/generation_time:.1f} 轨迹/秒")
        
        print(f"\n💾 轨迹数据已保存到 data/generated/trajectories/ 目录")
        
        
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断执行")
    except Exception as e:
        logger.error(f"轨迹生成失败: {e}")
        print(f"❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
