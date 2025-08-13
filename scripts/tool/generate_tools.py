#!/usr/bin/env python3
"""
工具生成脚本
基于已生成的场景数据生成大量工具
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from utils.logger import setup_logger
from utils.file_manager import FileManager
from modules.domain_tool_generator.tool_designer import ToolDesigner
from modules.domain_tool_generator.tool_registry import ToolRegistry


def setup_tool_logger():
    """设置工具生成专用日志器"""
    logger = setup_logger(
        "tool_generation",
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
    
    # 检查场景数据是否存在
    scenarios_path = settings.get_data_path('scenarios')
    if not scenarios_path.exists() or not any(scenarios_path.glob("*.json")):
        logger.error(f"未找到场景数据文件，请先运行 generate_scenarios.py")
        logger.error(f"场景数据路径: {scenarios_path}")
        return False
    
    # 检查并创建工具数据目录
    tools_path = settings.get_data_path('tools')
    if not tools_path.exists():
        tools_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建工具数据目录: {tools_path}")
    
    logger.info("环境验证完成")
    return True


def load_existing_scenarios(logger):
    """加载已生成的场景数据"""
    logger.info("加载已生成的场景数据...")
    
    scenarios_path = settings.get_data_path('scenarios')
    file_manager = FileManager(scenarios_path, logger)
    
    # 查找最新的场景文件
    scenario_files = list(scenarios_path.glob("scenarios_batch_*.json"))
    if not scenario_files:
        # 尝试查找汇总文件
        all_scenario_files = list(scenarios_path.glob("all_scenarios_*.json"))
        if all_scenario_files:
            # 使用最新的汇总文件
            latest_file = max(all_scenario_files, key=lambda f: f.stat().st_mtime)
            logger.info(f"使用汇总场景文件: {latest_file.name}")
            scenarios = file_manager.load_json(latest_file.name)
        else:
            raise FileNotFoundError("未找到场景数据文件")
    else:
        # 使用最新的批次文件
        latest_file = max(scenario_files, key=lambda f: f.stat().st_mtime)
        logger.info(f"使用场景批次文件: {latest_file.name}")
        scenarios = file_manager.load_json(latest_file.name)
    
    logger.info(f"成功加载 {len(scenarios)} 个场景")
    return scenarios


def generate_tools_for_scenarios(scenarios: List[Dict[str, Any]], logger):
    """基于场景生成工具"""
    logger.info("开始基于场景生成工具...")
    
    try:
        # 获取工具生成配置
        tool_config = settings.GENERATION_CONFIG['tools']
        
        input_data = {
            'scenarios': scenarios,
        }
        
        designer_config = {
            'batch_size': tool_config.get('batch_size', 20),
            'tools_per_scenario': tool_config.get('tools_per_scenario', 8),
        }
        
        with ToolDesigner(designer_config, logger) as designer:
            tools = designer.process(input_data)
            designer_stats = designer.get_generation_stats() if hasattr(designer, 'get_generation_stats') else {}
        
        return tools, designer_stats
        
    except Exception as e:
        logger.error(f"工具生成失败: {e}")
        raise


def register_generated_tools(tools: List[Dict[str, Any]], logger):
    """注册生成的工具"""
    logger.info("开始注册工具...")
    
    try:
        input_data = {'tools': tools}
        registry_config = {}
        
        with ToolRegistry(registry_config, logger) as registry:
            registration_result = registry.process(input_data)
            registry_stats = registry.get_registry_stats() if hasattr(registry, 'get_registry_stats') else {}
        
        return registration_result, registry_stats
        
    except Exception as e:
        logger.error(f"工具注册失败: {e}")
        raise


def analyze_generation_results(scenarios: List[Dict[str, Any]], tools: List[Dict[str, Any]], 
                             designer_stats: Dict[str, Any], registration_result: Dict[str, Any], logger):
    """分析工具生成结果"""
    logger.info("分析工具生成结果...")
    
    # 基本统计
    total_scenarios = len(scenarios)
    total_tools = len(tools)
    tools_per_scenario = total_tools / total_scenarios if total_scenarios > 0 else 0
    
    # 按领域统计
    domain_stats = {}
    category_stats = {}
    
    for tool in tools:
        metadata = tool.get('metadata', {})
        domain = metadata.get('domain', 'unknown')
        category = metadata.get('category', 'unknown')
        
        domain_stats[domain] = domain_stats.get(domain, 0) + 1
        category_stats[category] = category_stats.get(category, 0) + 1
    
    # 工具类型统计
    tool_types = {}
    for tool in tools:
        tool_type = tool.get('category', 'unknown')
        tool_types[tool_type] = tool_types.get(tool_type, 0) + 1
    
    analysis = {
        'generation_summary': {
            'total_scenarios_used': total_scenarios,
            'total_tools_generated': total_tools,
            'tools_per_scenario_avg': round(tools_per_scenario, 2),
            'registration_result': registration_result
        },
        'domain_distribution': domain_stats,
        'category_distribution': category_stats,
        'tool_type_distribution': tool_types,
        'designer_stats': designer_stats
    }
    
    # 输出结果摘要
    logger.info("=" * 60)
    logger.info("工具生成结果摘要")
    logger.info("=" * 60)
    logger.info(f"📊 总场景数: {total_scenarios}")
    logger.info(f"🔧 总工具数: {total_tools}")
    logger.info(f"📈 平均每场景工具数: {tools_per_scenario:.2f}")
    logger.info(f"✅ 成功注册工具数: {registration_result.get('registered_count', 0)}")
    
    logger.info("\n📂 领域分布:")
    for domain, count in sorted(domain_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
        logger.info(f"   {domain}: {count} 个工具")
    
    logger.info("\n🔨 工具类型分布:")
    for tool_type, count in sorted(tool_types.items(), key=lambda x: x[1], reverse=True)[:10]:
        logger.info(f"   {tool_type}: {count} 个工具")
    
    return analysis


def save_consolidated_results(tools: List[Dict[str, Any]], analysis: Dict[str, Any], logger):
    """保存汇总结果"""
    logger.info("保存汇总结果...")
    
    try:
        tools_path = settings.get_data_path('tools')
        file_manager = FileManager(tools_path, logger)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存分析结果
        analysis_file = f"generation_analysis_{timestamp}.json"
        file_manager.save_json(analysis, analysis_file)
        logger.info(f"保存分析结果: {analysis_file}")
        
        return {
            'analysis_file': str(tools_path / analysis_file),
            'timestamp': timestamp
        }
        
    except Exception as e:
        logger.error(f"保存结果失败: {e}")
        raise


def main():
    """主函数"""
    print("🔧 工具生成器")
    print("=" * 50)
    
    # 设置日志
    logger = setup_tool_logger()
    
    try:
        # 验证环境
        if not validate_environment(logger):
            return 1
        
        # 加载场景数据
        scenarios = load_existing_scenarios(logger)
        # 生成工具
        tools, designer_stats = generate_tools_for_scenarios(scenarios, logger)
        
        # # 注册工具
        # registration_result, registry_stats = register_generated_tools(tools, logger)
        
        # # 分析结果
        # analysis = analyze_generation_results(
        #     scenarios, tools, designer_stats, registration_result, logger
        # )
        
        # # 保存结果
        # save_info = save_consolidated_results(tools, analysis, logger)
        
        # 最终总结
        logger.info("=" * 60)
        logger.info("🎉 工具生成完成！")
        
        return 0
        
    except Exception as e:
        logger.error(f"工具生成过程失败: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 