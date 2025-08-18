#!/usr/bin/env python3
"""
轨迹评分脚本

加载生成的轨迹数据，进行预过滤和质量评分
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from utils.logger import setup_logger
from utils.file_manager import FileManager
from core.models import Trajectory, InteractionSession, ConversationTurn
from modules.quality_judge import TrajectoryEvaluator
from core.exceptions import QualityEvaluationError


def setup_scoring_logger():
    """设置轨迹评分专用日志器"""
    logger = setup_logger(
        "trajectory_scoring",
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


def load_trajectory_files(trajectories_dir: Path, logger: logging.Logger) -> List[Dict[str, Any]]:
    """
    加载轨迹目录下的所有JSON文件
    
    Args:
        trajectories_dir: 轨迹数据目录
        logger: 日志器
        
    Returns:
        轨迹数据列表
    """
    logger.info(f"开始加载轨迹文件: {trajectories_dir}")
    
    if not trajectories_dir.exists():
        logger.error(f"轨迹目录不存在: {trajectories_dir}")
        return []
    
    # 查找所有JSON文件
    json_files = list(trajectories_dir.glob("*.json"))
    logger.info(f"找到 {len(json_files)} 个JSON文件")
    
    trajectories_data = []
    failed_count = 0
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 确保数据包含必要字段
            if isinstance(data, dict):
                trajectories_data.append(data)
            else:
                logger.warning(f"跳过无效格式文件: {json_file.name}")
                failed_count += 1
                
        except Exception as e:
            logger.error(f"加载文件失败 {json_file.name}: {e}")
            failed_count += 1
    
    logger.info(f"成功加载 {len(trajectories_data)} 个轨迹文件")
    if failed_count > 0:
        logger.warning(f"加载失败 {failed_count} 个文件")
    
    return trajectories_data


def convert_dict_to_trajectory(trajectory_data: Dict[str, Any]) -> Optional[Trajectory]:
    """将轨迹字典转换为Trajectory对象"""
    try:
        # 提取基本信息
        trajectory_id = trajectory_data.get('trajectory_id') or trajectory_data.get('id')
        if not trajectory_id:
            return None
        
        session_data = {
            'id': trajectory_data.get('session_id', f"{trajectory_id}_session"),
            'task_id': trajectory_data.get('task_id', ''),
            'agent_id': trajectory_data.get('agent_id', ''),
            'turns': trajectory_data.get('messages', trajectory_data.get('turns', [])),
        }
        
        # 转换对话轮次
        turns = []
        turns_data = session_data.get('turns', [])
        
        for turn_data in turns_data:
            if isinstance(turn_data, dict):
                # 处理不同的数据格式
                if 'role' in turn_data:
                    # 训练数据格式
                    speaker_map = {
                        'user': 'user',
                        'assistant': 'agent',
                        'execution': 'execution'
                    }
                    speaker = speaker_map.get(turn_data.get('role'), turn_data.get('role'))
                    message = turn_data.get('content', '')
                    recipient = turn_data.get('recipient', '')
                else:
                    # 原始格式
                    speaker = turn_data.get('speaker', 'unknown')
                    message = turn_data.get('message', '')
                    recipient = turn_data.get('recipient', '')
                
                turn = ConversationTurn(
                    speaker=speaker,
                    recipient=recipient,
                    message=message,
                    timestamp=turn_data.get('timestamp')
                )
                turns.append(turn)
        
        session = InteractionSession(
            id=session_data.get('id', f"{trajectory_id}_session"),
            task_id=session_data.get('task_id', ''),
            agent_id=session_data.get('agent_id', ''),
            turns=turns,
            metadata=session_data.get('metadata', {})
        )
        
        # 创建轨迹对象
        trajectory = Trajectory(
            id=trajectory_id,
            session=session,
            created_at=datetime.now()
        )
        
        return trajectory
        
    except Exception as e:
        print(f"⚠️ 转换轨迹失败 {trajectory_data.get('trajectory_id', trajectory_data.get('id', 'unknown'))}: {e}")
        return None


def prefilter_trajectories(
    trajectories: List[Trajectory], 
    evaluator: TrajectoryEvaluator,
    logger: logging.Logger
) -> List[Trajectory]:
    """
    使用预过滤器过滤轨迹
    
    Args:
        trajectories: 轨迹列表
        evaluator: 轨迹评估器
        logger: 日志器
        
    Returns:
        通过预过滤的轨迹列表
    """
    logger.info(f"开始预过滤 {len(trajectories)} 个轨迹")
    
    filtered_trajectories = []
    filter_stats = {
        'total': len(trajectories),
        'passed': 0,
        'failed': 0,
        'failure_reasons': {}
    }
    
    for trajectory in trajectories:
        try:
            if evaluator.prefilter_trajectory(trajectory):
                filtered_trajectories.append(trajectory)
                filter_stats['passed'] += 1
            else:
                filter_stats['failed'] += 1
                
        except Exception as e:
            filter_stats['failed'] += 1
    
    pass_rate = filter_stats['passed'] / filter_stats['total'] if filter_stats['total'] > 0 else 0
    logger.info(f"预过滤完成: {filter_stats['passed']}/{filter_stats['total']} 通过 (通过率: {pass_rate:.1%})")
    
    return filtered_trajectories


def score_single_trajectory(
    logger: logging.Logger,
    evaluator: TrajectoryEvaluator,
    trajectory: Trajectory
) -> Optional[Dict[str, Any]]:
    """评估单个轨迹"""
    try:
        # 执行评估
        scored_trajectory = evaluator.evaluate_trajectory(trajectory)
        
        return {
            'trajectory_id': trajectory.id,
            'turns_count': len(trajectory.session.turns),
            'score': scored_trajectory.evaluation_score.overall_score if scored_trajectory.evaluation_score else 0,
            'status': 'success'
        }
        
    except Exception as e:
        logger.error(f"评估轨迹失败 - ID: {trajectory.id}, 错误: {e}")
        return {
            'trajectory_id': trajectory.id,
            'status': 'failed',
            'error': str(e)
        }

def main():
    """主函数"""
    print("🎯 轨迹评分器")
    print("="*60)
    
    # 验证环境
    if not validate_environment():
        return 1
    
    # 设置日志
    logger = setup_scoring_logger()
    
    try:
        # 1. 加载轨迹数据
        print("📁 加载轨迹数据...")
        
        trajectories_dir = settings.get_data_path('trajectories')
        trajectories_data = load_trajectory_files(trajectories_dir, logger)
        
        if not trajectories_data:
            print("❌ 未找到轨迹数据文件")
            return 1
        
        print(f"✅ 加载了 {len(trajectories_data)} 个轨迹文件")
        
        # 2. 转换数据格式
        print("🔄 转换轨迹数据格式...")
        trajectories = []
        
        for traj_data in trajectories_data:
            trajectory = convert_dict_to_trajectory(traj_data)
            if trajectory:
                trajectories.append(trajectory)
        
        valid_trajectories_count = len(trajectories)
        print(f"✅ 成功转换 {valid_trajectories_count} 个有效轨迹")
        
        if not trajectories:
            print("❌ 没有有效的轨迹数据")
            return 1
        
        # 3. 初始化评估器
        print("⚖️ 初始化轨迹评估器...")
        
        evaluator_config = {
            "llm_config": settings.get_llm_config(),
            "quality_config": settings.QUALITY_CONFIG
        }
        
        evaluator = TrajectoryEvaluator(evaluator_config, logger)
        evaluator.initialize()
        
        print("✅ 评估器初始化完成")
        
        # 4. 预过滤轨迹
        print("🔍 预过滤轨迹...")
        filtered_trajectories = prefilter_trajectories(trajectories, evaluator, logger)
        
        if not filtered_trajectories:
            print("❌ 没有轨迹通过预过滤")
            return 1
        filtered_trajectories = filtered_trajectories[:10]
        print(f"✅ {len(filtered_trajectories)} 个轨迹通过预过滤")

        # 5. 执行评分
        max_workers = settings.CONCURRENCY_CONFIG.get('max_workers', 4)
        print(f"🎯 开始轨迹评分...")
        
        start_time = datetime.now()
        
        scoring_results = []
        successful_count = 0
        failed_count = 0
        
        # 使用多线程进行评分
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_trajectory = {}
            
            for trajectory in filtered_trajectories:
                future = executor.submit(
                    score_single_trajectory,
                    logger,
                    evaluator,
                    trajectory
                )
                future_to_trajectory[future] = trajectory.id
            
            # 收集评分结果
            for i, future in enumerate(as_completed(future_to_trajectory), 1):
                try:
                    result = future.result()
                    if result:
                        scoring_results.append(result)
                        
                        if result['status'] == 'success':
                            successful_count += 1
                            if successful_count % 5 == 0:  # 每5个成功评分输出进度
                                print(f"✅ 已完成评分 {successful_count} 个轨迹...")
                        else:
                            failed_count += 1
                        
                        # 输出总进度
                        if i % 10 == 0:
                            print(f"📊 总进度: {i}/{len(filtered_trajectories)} ({i/len(filtered_trajectories)*100:.1f}%)")
                            
                except Exception as e:
                    failed_count += 1
                    logger.error(f"轨迹评分任务异常: {e}")
        
        print(f"✅ 评分完成: {successful_count} 个轨迹成功, {failed_count} 个轨迹失败")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断执行")
        return 1
    except Exception as e:
        logger.error(f"轨迹评分失败: {e}")
        print(f"❌ 评分失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
