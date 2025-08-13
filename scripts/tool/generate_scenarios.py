#!/usr/bin/env python3
"""
场景生成脚本
基于配置中的所有领域生成大量场景数据
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from utils.logger import setup_logger
from modules.domain_tool_generator.scenario_generator import ScenarioGenerator


def setup_scenario_logger():
    """设置场景生成专用日志器"""
    logger = setup_logger(
        "scenario_generation",
        level=settings.LOGGING_CONFIG["level"],
        log_file=settings.LOGGING_CONFIG["file_path"],
        format_string=settings.LOGGING_CONFIG["format"]
    )
    return logger


def validate_environment(logger):
    """验证运行环境"""
    logger.info("验证环境配置...")
    
    # 检查API密钥
    llm_config = settings.get_llm_config()
    if not llm_config.get("api_key"):
        logger.error(f"缺少{settings.DEFAULT_LLM_PROVIDER} API密钥")
        logger.error("请设置环境变量：OPENAI_API_KEY 或 CLAUDE_API_KEY")
        return False
    
    logger.info("环境验证完成")
    return True


def generate_scenarios_for_all_domains(logger):
    """为所有领域生成场景"""
    logger.info("开始大规模场景生成...")
    
    # 获取配置
    scenario_config = settings.GENERATION_CONFIG['scenarios']
    domains = scenario_config['domains']
    target_total = scenario_config['target_count']
    
    logger.info(f"目标生成 {target_total} 个场景，覆盖 {len(domains)} 个领域")
    
    try:
        # 初始化场景生成器
        generator_config = {
            'batch_size': scenario_config.get('batch_size', 10),
        }
        
        with ScenarioGenerator(generator_config, logger) as generator:
            # 准备输入数据
            input_data = {
                'domains': domains,
                'target_count': target_total
            }
            
            # 执行生成
            logger.info("正在生成场景...")
            scenarios = generator.process(input_data)
            
            # 获取生成统计
            stats = generator.get_generation_stats()
            
            return scenarios, stats
            
    except Exception as e:
        logger.error(f"场景生成失败: {e}")
        raise


def analyze_generation_results(scenarios: List[Dict[str, Any]], stats: Dict[str, Any], logger):
    """分析生成结果"""
    logger.info("\n" + "="*50)
    logger.info("场景生成结果分析")
    logger.info("="*50)
    
    # 基本统计
    total_scenarios = len(scenarios)
    logger.info(f"📊 总体统计:")
    logger.info(f"   生成场景总数: {total_scenarios}")
    logger.info(f"   生成批次数: {stats.get('batch_files', 0)}")
    
    # 领域分布
    domain_distribution = {}
    for scenario in scenarios:
        domain = scenario.get('domain', '未知')
        domain_distribution[domain] = domain_distribution.get(domain, 0) + 1
    
    logger.info(f"\n🌐 领域分布:")
    for domain, count in sorted(domain_distribution.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_scenarios) * 100 if total_scenarios > 0 else 0
        logger.info(f"   {domain}: {count} 个场景 ({percentage:.1f}%)")
    
    logger.info("\n" + "="*50)


def main():
    """主函数"""
    try:
        # 设置日志
        logger = setup_scenario_logger()
        
        logger.info("🚀 启动大规模场景生成脚本")
        logger.info("="*60)
        
        # 验证环境
        if not validate_environment(logger):
            sys.exit(1)
        
        # 生成场景
        scenarios, stats = generate_scenarios_for_all_domains(logger)
        
        # 分析结果
        analyze_generation_results(scenarios, stats, logger)
        
        # 最终总结
        logger.info(f"\n🎉 场景生成完成!")
        logger.info(f"✅ 成功生成 {len(scenarios)} 个场景")

        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断程序执行")
        return 0
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 