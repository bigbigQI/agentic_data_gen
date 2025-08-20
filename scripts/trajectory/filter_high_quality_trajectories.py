#!/usr/bin/env python3
"""
高质量轨迹过滤脚本

从 trajectory_evaluations 目录读取所有已评分的轨迹数据，
将评分 > 4.0 的轨迹文件复制到 high_quality_trajectories 目录
"""

import os
import sys
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from utils.logger import setup_logger
from utils.file_manager import FileManager


def setup_filter_logger():
    """设置高质量轨迹过滤专用日志器"""
    logger = setup_logger(
        "trajectory_filter",
        level=settings.LOGGING_CONFIG["level"],
        log_file=settings.LOGGING_CONFIG["file_path"]
    )
    return logger


def filter_high_quality_trajectories(
    source_dir: Path, 
    target_dir: Path, 
    score_threshold: float,
    logger: logging.Logger
) -> Dict[str, Any]:
    """
    过滤并复制高质量轨迹文件
    
    Args:
        source_dir: 源目录（trajectory_evaluations）
        target_dir: 目标目录（high_quality_trajectories）
        score_threshold: 分数阈值
        logger: 日志器
        
    Returns:
        过滤结果统计
    """
    logger.info(f"开始过滤高质量轨迹: {source_dir} -> {target_dir}")
    logger.info(f"分数阈值: > {score_threshold}")
    
    # 检查源目录
    if not source_dir.exists():
        logger.error(f"源目录不存在: {source_dir}")
        return {}
    
    # 确保目标目录存在
    target_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"目标目录已准备: {target_dir}")
    
    # 查找所有JSON文件
    json_files = list(source_dir.glob("*.json"))
    logger.info(f"找到 {len(json_files)} 个评分文件")
    
    for json_file in json_files:
        try:
            # 读取文件内容
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                        
            # 检查是否为有效的评分轨迹数据
            if not isinstance(data, dict):
                logger.warning(f"跳过无效格式文件: {json_file.name}")
                continue
            
            # 提取分数
            score = data.get('score', 0.0)
            
            # 确保分数是数值类型
            if not isinstance(score, (int, float)):
                logger.warning(f"文件 {json_file.name} 分数格式无效: {score}")
                continue
            
            # 检查是否满足高质量标准
            if float(score) > score_threshold:
                target_file = target_dir / json_file.name
                shutil.copy2(json_file, target_file)
                
                logger.debug(f"复制高质量轨迹: {json_file.name} (分数: {score:.2f})")
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败 {json_file.name}: {e}")
            
        except Exception as e:
            logger.error(f"处理文件失败 {json_file.name}: {e}")

    return None


def main():
    """主函数"""
    print("🔍 高质量轨迹过滤器")
    print("="*60)
    
    # 设置日志
    logger = setup_filter_logger()
    
    try:
        # 1. 设置目录路径
        source_dir = settings.get_data_path('trajectory_evaluations')
        target_dir = settings.get_data_path('high_quality_trajectories')
        
        print(f"📁 源目录: {source_dir}")
        print(f"📁 目标目录: {target_dir}")
        
        # 2. 执行过滤
        print(f"🔍 开始过滤高质量轨迹 (分数 > 4.0)...")
        
        filter_high_quality_trajectories(
            source_dir=source_dir,
            target_dir=target_dir,
            score_threshold=4.0,
            logger=logger
        )
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断执行")
        return 1
    except Exception as e:
        logger.error(f"高质量轨迹过滤失败: {e}")
        print(f"❌ 过滤失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
