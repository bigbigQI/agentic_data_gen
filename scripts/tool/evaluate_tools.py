#!/usr/bin/env python3
"""
工具质量评估脚本
使用多线程方式批量评估工具质量
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from modules.domain_tool_generator.tool_designer import ToolDesigner
from utils.logger import setup_logger
from utils.file_manager import FileManager


def load_tools_from_file(file_path: str):
    """从指定文件加载工具数据"""
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        tools_data = json.load(f)
    
    print(f"✅ 成功加载 {len(tools_data)} 个工具")
    return tools_data



def validate_environment():
    """验证环境配置"""
    
    if not os.getenv('OPENAI_API_KEY'):
        print(f"❌ 缺少环境变量: OPENAI_API_KEY")
        print("请确保在 .env 文件中设置 OPENAI_API_KEY")
        return False
    
    print("✅ 环境变量检查通过")
    return True


def display_analysis_results(analysis: dict):
    """显示分析结果"""
    print("\n📈 工具质量评估结果分析")
    print("="*60)
    
    print(f"📊 基础统计:")
    print(f"  总工具数量: {analysis.get('total_count', 0)}")
    print(f"  平均质量分数: {analysis.get('average_score', 0)}")
    print(f"  分数范围: {analysis.get('min_score', 0)} - {analysis.get('max_score', 0)}")
    
    quality_summary = analysis.get('quality_summary', {})
    print(f"\n🎯 质量概览:")
    print(f"  高质量工具比例: {quality_summary.get('high_quality_ratio', 0)}%")
    print(f"  需要改进比例: {quality_summary.get('needs_improvement_ratio', 0)}%")
    
    score_dist = analysis.get('score_distribution', {})
    print(f"\n📊 分数分布:")
    print(f"  🌟 优秀 (≥4.5分): {score_dist.get('excellent', 0)} 个")
    print(f"  ✅ 良好 (4.0-4.5分): {score_dist.get('good', 0)} 个") 
    print(f"  ⚠️  一般 (3.0-4.0分): {score_dist.get('average', 0)} 个")
    print(f"  ❌ 较差 (<3.0分): {score_dist.get('poor', 0)} 个")
    
    recommendations = analysis.get('recommendations', {})
    if recommendations:
        print(f"\n💡 推荐状态分布:")
        for rec, count in recommendations.items():
            print(f"  {rec}: {count} 个")


def save_evaluation_results(evaluations: list, analysis: dict):
    """保存评估结果"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tools_dir = settings.get_data_path('tools')
    file_manager = FileManager(tools_dir)
    
    # 保存详细评估结果
    eval_filename = f"tool_evaluations_{timestamp}.json"
    file_manager.save_json(evaluations, eval_filename)
    print(f"💾 详细评估结果已保存: {eval_filename}")
    
    # 保存分析报告
    analysis_filename = f"evaluation_analysis_{timestamp}.json"
    file_manager.save_json(analysis, analysis_filename)
    print(f"💾 分析报告已保存: {analysis_filename}")
    
    return eval_filename, analysis_filename


def main():
    """主函数"""
    print("🔍 工具质量评估开始")
    print("="*60)
    
    # 验证环境
    if not validate_environment():
        return
    
    # 设置日志
    logger = setup_logger(
        "tool_evaluation",
        level=settings.LOGGING_CONFIG["level"],
        log_file=settings.LOGGING_CONFIG["file_path"]
    )
    
    try:
        # 1. 加载指定的工具文件
        tools_file = "data/generated/tools/tools_batch_20250810_114153.json"
        tools_data = load_tools_from_file(tools_file)
        if not tools_data:
            print("❌ 无法加载工具数据，程序退出")
            return
        
        # 2. 初始化工具设计器
        print("⚙️ 初始化工具设计器...")
        tool_designer = ToolDesigner(logger=logger)
        tool_designer.initialize()
        
        print(f"🎯 准备评估 {len(tools_data)} 个工具")
        print(f"🔧 使用 {tool_designer.max_workers} 个线程并行处理")
        
        # 3. 批量评估工具质量
        print("\n🔄 开始批量评估工具质量...")
        start_time = datetime.now()
        
        evaluations = tool_designer.batch_evaluate_tools(tools_data)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print(f"\n⏱️ 评估耗时: {processing_time:.2f} 秒")
        print(f"📈 成功率: {len(evaluations)}/{len(tools_data)} ({len(evaluations)/len(tools_data)*100:.1f}%)")
        
        # 4. 分析评估结果
        analysis = tool_designer.analyze_evaluation_results(evaluations)
        display_analysis_results(analysis)
        
        # 5. 保存结果
        print(f"\n💾 保存评估结果...")
        eval_file, analysis_file = save_evaluation_results(evaluations, analysis)
        
        print(f"\n✅ 工具质量评估完成！")
        print(f"📁 结果文件:")
        print(f"  - 详细评估: {eval_file}")
        print(f"  - 分析报告: {analysis_file}")
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断执行")
    except Exception as e:
        logger.error(f"工具评估失败: {e}")
        print(f"❌ 评估失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()