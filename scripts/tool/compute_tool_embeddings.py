#!/usr/bin/env python3
"""
工具嵌入向量计算脚本
读取最新的工具JSON文件，计算每个工具的embedding向量并保存结果
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List
import json
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from utils.logger import setup_logger
from utils.file_manager import FileManager
from modules.domain_tool_generator.tool_embedding import ToolEmbedding


def setup_embedding_logger():
    """设置嵌入向量计算专用日志器"""
    logger = setup_logger(
        "tool_embedding",
        level=settings.LOGGING_CONFIG["level"],
        log_file=settings.LOGGING_CONFIG["file_path"],
        format_string=settings.LOGGING_CONFIG["format"]
    )
    return logger


def validate_environment(logger):
    """验证运行环境"""
    logger.info("验证环境配置...")
    
    # 检查DashScope API密钥
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        logger.error("缺少DashScope API密钥")
        logger.error("请设置环境变量：DASHSCOPE_API_KEY")
        return False

    return True


def find_latest_tools_file(logger):
    """查找最新的工具数据文件"""
    logger.info("查找最新的工具数据文件...")
    
    tools_path = settings.get_data_path('tools')
    file_manager = FileManager(tools_path, logger)
    
    # 优先查找已优化的工具文件
    batch_files = list(tools_path.glob("tools_batch_*.json"))
    if batch_files:
        latest_file = max(batch_files, key=lambda f: f.stat().st_mtime)
        logger.info(f"使用已优化工具文件: {latest_file.name}")
        return latest_file
    
    raise FileNotFoundError("未找到任何工具数据文件")


def load_tools_data(file_path: Path, logger):
    """加载工具数据"""
    logger.info(f"加载工具数据: {file_path.name}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tools = json.load(f)
        
        logger.info(f"成功加载 {len(tools)} 个工具")
        return tools
        
    except Exception as e:
        logger.error(f"加载工具数据失败: {e}")
        raise


def compute_embeddings_for_tools(tools: List[Dict[str, Any]], logger):
    """为工具计算embedding向量"""
    logger.info("开始计算工具embedding向量...")
    
    try:
        # 初始化embedding模块
        embedding_config = {
            'batch_size': 10,  # 控制API调用频率
            'embedding_model': 'text-embedding-v4',
            'embedding_dimensions': 256
        }
        
        input_data = {'tools': tools}
        
        with ToolEmbedding(embedding_config, logger) as embedding_module:
            # 直接处理工具列表，而不是从文件加载
            updated_tools = embedding_module._add_embeddings_to_tools(tools)
            
        return updated_tools
        
    except Exception as e:
        logger.error(f"embedding计算失败: {e}")
        raise


def merge_with_existing_tools(new_tools: List[Dict[str, Any]], 
                             all_tools: List[Dict[str, Any]], logger):
    """将新计算的embedding合并到所有工具中"""
    logger.info("合并embedding结果...")
    
    # 创建新工具的ID到工具的映射
    new_tools_map = {tool['id']: tool for tool in new_tools}
    
    # 更新原有工具列表
    updated_tools = []
    for tool in all_tools:
        tool_id = tool.get('id')
        if tool_id in new_tools_map:
            # 使用新计算的embedding
            updated_tools.append(new_tools_map[tool_id])
        else:
            # 保留原有工具（可能已有embedding）
            updated_tools.append(tool)
    
    # 统计embedding覆盖率
    tools_with_embedding = len([
        t for t in updated_tools 
        if t.get('metadata', {}).get('embedding')
    ])
    
    logger.info(f"合并完成:")
    logger.info(f"  总工具数: {len(updated_tools)}")
    logger.info(f"  有embedding的工具: {tools_with_embedding}")
    logger.info(f"  embedding覆盖率: {tools_with_embedding/len(updated_tools)*100:.1f}%")
    
    return updated_tools


def analyze_embedding_results(tools: List[Dict[str, Any]], logger):
    """分析embedding计算结果"""
    logger.info("分析embedding计算结果...")
    
    # 基本统计
    total_tools = len(tools)
    tools_with_embedding = len([
        t for t in tools 
        if t.get('metadata', {}).get('embedding')
    ])
    
    analysis = {
        'embedding_summary': {
            'total_tools': total_tools,
            'tools_with_embedding': tools_with_embedding,
            'embedding_coverage': round(tools_with_embedding / total_tools * 100, 2) if total_tools > 0 else 0,
            'embedding_model': 'text-embedding-v4',
            'embedding_dimensions': 256
        },
        'processed_at': datetime.now().isoformat()
    }
    
    # 输出结果摘要
    logger.info("=" * 60)
    logger.info("Embedding计算结果摘要")
    logger.info("=" * 60)
    logger.info(f"🔧 总工具数: {total_tools}")
    logger.info(f"✅ 有embedding的工具: {tools_with_embedding}")
    logger.info(f"📊 覆盖率: {analysis['embedding_summary']['embedding_coverage']}%")

    return analysis


def save_embedding_results(tools: List[Dict[str, Any]], logger):
    """保存embedding计算结果"""
    logger.info("保存embedding计算结果...")
    
    try:
        tools_path = settings.get_data_path('tools')
        file_manager = FileManager(tools_path, logger)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存包含embedding的工具数据
        tools_file = f"tools_with_embeddings_{timestamp}.json"
        file_manager.save_json(tools, tools_file)
        logger.info(f"保存工具数据: {tools_file}")
        
        return {
            'tools_file': str(tools_path / tools_file),
            'timestamp': timestamp
        }
        
    except Exception as e:
        logger.error(f"保存结果失败: {e}")
        raise


def main():
    """主函数"""
    print("🧮 工具Embedding计算器")
    print("=" * 50)
    
    # 设置日志
    logger = setup_embedding_logger()
    
    try:
        # 验证环境
        if not validate_environment(logger):
            return 1
        
        # 查找最新工具文件
        tools_file = find_latest_tools_file(logger)
        
        # 加载工具数据
        all_tools = load_tools_data(tools_file, logger)
        
        # 计算embedding
        tools_with_new_embeddings = compute_embeddings_for_tools(all_tools, logger)
        # 合并结果
        all_updated_tools = merge_with_existing_tools(tools_with_new_embeddings, all_tools, logger)
        
        # 分析结果
        analysis = analyze_embedding_results(all_updated_tools, logger)
        
        # 保存结果
        save_info = save_embedding_results(all_updated_tools, logger)
        
        # 最终总结
        logger.info("=" * 60)
        logger.info("🎉 Embedding计算完成！")
        logger.info(f"📁 工具数据: {save_info['tools_file']}")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Embedding计算过程失败: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)