"""
大规模智能体数据合成项目主程序
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from utils.logger import setup_logger
from modules.domain_tool_generator import DomainToolGeneratorModule


def setup_environment():
    """设置运行环境"""
    # 设置日志
    logger = setup_logger(
        "main",
        level=settings.LOGGING_CONFIG["level"],
        log_file=settings.LOGGING_CONFIG["file_path"],
        format_string=settings.LOGGING_CONFIG["format"]
    )
    
    logger.info("=" * 60)
    logger.info("大规模智能体数据合成项目启动")
    logger.info("=" * 60)
    
    return logger


def validate_configuration(logger):
    """验证配置"""
    logger.info("验证配置...")
    
    # 检查API密钥
    llm_config = settings.get_llm_config()
    if not llm_config.get("api_key"):
        logger.error(f"缺少{settings.DEFAULT_LLM_PROVIDER} API密钥")
        logger.error("请设置环境变量或修改配置文件")
        return False
    
    # 检查数据目录
    for data_type, path in settings.DATA_PATHS.items():
        if not path.exists():
            logger.warning(f"数据目录不存在，将创建: {path}")
            path.mkdir(parents=True, exist_ok=True)
    
    logger.info("配置验证完成")
    return True


def run_domain_tool_generation(logger):
    """运行场景与工具生成"""
    logger.info("开始场景与工具生成...")
    
    try:
        # 配置输入数据
        input_data = {
            'domains': settings.GENERATION_CONFIG['scenarios']['domains'][:5],  # 先测试5个领域
            'target_scenario_count': 50,  # 测试生成50个场景
            'target_tool_count': 200   # 测试生成200个工具
        }
        
        # 创建模块实例
        module_config = {
            'scenario_generator': settings.GENERATION_CONFIG['scenarios'],
            'tool_designer': settings.GENERATION_CONFIG['tools']
        }
        
        with DomainToolGeneratorModule(module_config, logger) as module:
            # 执行生成
            results = module.process(input_data)
            
            # 输出结果统计
            stats = results.get('stats', {})
            logger.info(f"生成完成!")
            logger.info(f"- 场景数量: {stats.get('scenario_count', 0)}")
            logger.info(f"- 工具数量: {stats.get('tool_count', 0)}")
            logger.info(f"- 覆盖领域: {stats.get('domain_count', 0)}")
            
            # 验证结果
            validation_results = results.get('validation_results', {})
            if validation_results:
                quality_score = validation_results.get('quality_assessment', {}).get('overall_quality_score', 0)
                logger.info(f"- 整体质量分数: {quality_score:.2f}")
            
            return results
            
    except Exception as e:
        logger.error(f"场景与工具生成失败: {e}")
        raise


def display_results_summary(results: Dict[str, Any], logger):
    """显示结果摘要"""
    logger.info("\n" + "=" * 60)
    logger.info("生成结果摘要")
    logger.info("=" * 60)
    
    scenarios = results.get('scenarios', [])
    tools = results.get('tools', [])
    validation_results = results.get('validation_results', {})
    
    # 场景统计
    logger.info(f"📊 场景统计:")
    logger.info(f"   总数量: {len(scenarios)}")
    if scenarios:
        domains = set(s.get('domain', '') for s in scenarios)
        categories = set(s.get('category', '') for s in scenarios)
        logger.info(f"   覆盖领域: {len(domains)} ({', '.join(list(domains)[:3])}...)")
        logger.info(f"   场景类别: {len(categories)}")
    
    # 工具统计
    logger.info(f"\n🔧 工具统计:")
    logger.info(f"   总数量: {len(tools)}")
    if tools:
        tool_categories = set(t.get('category', '') for t in tools)
        avg_params = sum(len(t.get('parameters', [])) for t in tools) / len(tools)
        logger.info(f"   工具类别: {len(tool_categories)}")
        logger.info(f"   平均参数数: {avg_params:.1f}")
    
    # 质量评估
    if validation_results:
        quality_assessment = validation_results.get('quality_assessment', {})
        scenario_validation = validation_results.get('scenario_validation', {})
        tool_validation = validation_results.get('tool_validation', {})
        
        logger.info(f"\n📈 质量评估:")
        logger.info(f"   整体质量: {quality_assessment.get('overall_quality_score', 0):.2f}/1.0")
        logger.info(f"   场景通过率: {scenario_validation.get('passed', 0)}/{scenario_validation.get('total_scenarios', 0)}")
        logger.info(f"   工具通过率: {tool_validation.get('passed', 0)}/{tool_validation.get('total_tools', 0)}")
        
        # 显示建议
        recommendations = validation_results.get('recommendations', [])
        if recommendations:
            logger.info(f"\n💡 改进建议:")
            for i, rec in enumerate(recommendations[:3], 1):
                logger.info(f"   {i}. {rec}")
    
    logger.info("\n" + "=" * 60)


def main():
    """主函数"""
    try:
        # 设置环境
        logger = setup_environment()
        
        # 验证配置
        if not validate_configuration(logger):
            sys.exit(1)
        
        # 运行场景与工具生成
        results = run_domain_tool_generation(logger)
        
        # 显示结果摘要
        display_results_summary(results, logger)
        
        logger.info("程序执行完成! 🎉")
        
    except KeyboardInterrupt:
        print("\n用户中断程序执行")
        sys.exit(0)
    except Exception as e:
        print(f"程序执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 