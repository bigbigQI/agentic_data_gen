#!/usr/bin/env python3
"""
工具关系图构建脚本
读取包含embedding的工具数据，构建工具关系图并保存
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
from modules.agent_synthesizer.tool_graph import ToolGraph


def setup_graph_logger():
    """设置工具图构建专用日志器"""
    logger = setup_logger(
        "tool_graph",
        level=settings.LOGGING_CONFIG["level"],
        log_file=settings.LOGGING_CONFIG["file_path"],
        format_string=settings.LOGGING_CONFIG["format"]
    )
    return logger


def validate_environment(logger):
    """验证运行环境"""
    logger.info("验证环境配置...")
    
    # 检查工具数据是否存在
    tools_path = settings.get_data_path('tools')
    if not tools_path.exists():
        logger.error(f"工具数据路径不存在: {tools_path}")
        return False
        
    return True


def find_latest_embedding_file(logger):
    """查找最新的embedding数据文件"""
    logger.info("查找最新的embedding数据文件...")
    
    tools_path = settings.get_data_path('tools')
    
    # 查找embedding文件
    embedding_files = list(tools_path.glob("tools_with_embeddings_*.json"))
    if embedding_files:
        latest_file = max(embedding_files, key=lambda f: f.stat().st_mtime)
        logger.info(f"使用embedding文件: {latest_file.name}")
        return latest_file
    
    raise FileNotFoundError("未找到包含embedding的工具数据文件")


def load_tools_with_embeddings(file_path: Path, logger):
    """加载包含embedding的工具数据"""
    logger.info(f"加载工具数据: {file_path.name}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tools = json.load(f)
        
        # 验证embedding数据
        tools_with_embedding = [
            tool for tool in tools 
            if tool.get('metadata', {}).get('embedding')
        ]
        
        logger.info(f"成功加载 {len(tools)} 个工具")
        
        if len(tools_with_embedding) == 0:
            raise ValueError("没有找到包含embedding的工具")
        
        return tools
        
    except Exception as e:
        logger.error(f"加载工具数据失败: {e}")
        raise


def build_tool_graph(tools: List[Dict[str, Any]], logger):
    """构建工具关系图"""
    logger.info("开始构建工具关系图...")
    
    try:
        # 图构建配置
        graph_config = {
            'similarity_threshold': 0.7,          # 相似度阈值
            'min_similarity_threshold': 0.5,     # 最小相似度阈值
            'max_edges_per_node': 10,             # 每个节点最大边数
            'restart_probability': 0.15,          # 随机游走重启概率
            'walk_length': 6                      # 游走长度
        }
        
        input_data = {'tools': tools}
        
        with ToolGraph(graph_config, logger) as graph_module:
            graph_stats = graph_module.process(input_data)
            
        return graph_stats, graph_module
        
    except Exception as e:
        logger.error(f"工具图构建失败: {e}")
        raise


def test_graph_functionality(graph_module: ToolGraph, logger):
    """测试图功能"""
    logger.info("测试图功能...")
    
    try:
        if graph_module.graph.number_of_nodes() == 0:
            logger.warning("图中没有节点，跳过功能测试")
            return {}
        
        # 随机选择一个节点进行测试
        test_nodes = list(graph_module.graph.nodes())[:3]  # 测试前3个节点
        
        test_results = []
        for node in test_nodes:
            # 测试随机游走
            related_tools = graph_module.random_walk_selection(node, count=5)
            
            # 测试获取相关工具
            direct_related = graph_module.get_related_tools(node, max_count=3)
            
            # 测试工具簇
            tool_cluster = graph_module.get_tool_cluster(node, max_size=6)
            
            tool_info = graph_module.tools_data.get(node, {})
            test_results.append({
                'tool_id': node,
                'tool_name': tool_info.get('name', 'Unknown'),
                'tool_category': tool_info.get('category', 'Unknown'),
                'random_walk_results': related_tools,
                'direct_related_count': direct_related,
                'cluster_size': len(tool_cluster)
            })
        
        logger.info("图功能测试结果:")
        for result in test_results:
            logger.info(f"  工具: {result['tool_name'][:30]} ({result['tool_category']})")
            logger.info(f"    随机游走选择: {result['random_walk_results']} 个相关工具")
            logger.info(f"    直接相关: {result['direct_related_count']} 个工具")
            logger.info(f"    工具簇大小: {result['cluster_size']} 个工具")
        
        return {
            'test_results': test_results,
            'total_tested_nodes': len(test_nodes)
        }
        
    except Exception as e:
        logger.error(f"图功能测试失败: {e}")
        return {}


def analyze_graph_quality(graph_stats: Dict[str, Any], graph_module: ToolGraph, logger):
    """分析图质量"""
    logger.info("分析图质量...")
    
    try:
        # 基本图统计
        total_nodes = graph_stats.get('total_nodes', 0)
        total_edges = graph_stats.get('total_edges', 0)
        avg_degree = graph_stats.get('average_degree', 0)
        connected_components = graph_stats.get('connected_components', 0)
        largest_component = graph_stats.get('largest_component_size', 0)
        
        # 计算图质量指标
        graph_density = (2 * total_edges) / (total_nodes * (total_nodes - 1)) if total_nodes > 1 else 0
        connectivity_ratio = largest_component / total_nodes if total_nodes > 0 else 0
        
        # 边类型分布
        edge_types = graph_stats.get('edge_types', {})
        
        analysis = {
            'graph_quality': {
                'total_nodes': total_nodes,
                'total_edges': total_edges,
                'average_degree': round(avg_degree, 2),
                'graph_density': round(graph_density, 4),
                'connected_components': connected_components,
                'largest_component_size': largest_component,
                'connectivity_ratio': round(connectivity_ratio, 4)
            },
            'edge_distribution': edge_types,
            'analyzed_at': datetime.now().isoformat()
        }
        
        # 输出分析结果
        logger.info("=" * 60)
        logger.info("工具关系图质量分析")
        logger.info("=" * 60)
        logger.info(f"🔗 节点数: {total_nodes}")
        logger.info(f"🔀 边数: {total_edges}")
        logger.info(f"📊 平均度: {avg_degree:.2f}")
        logger.info(f"🕸️ 图密度: {graph_density:.4f}")
        logger.info(f"🔗 连通组件数: {connected_components}")
        logger.info(f"🏢 最大连通组件: {largest_component} ({connectivity_ratio:.1%})")
        
        logger.info("\n🔗 边类型分布:")
        for edge_type, count in edge_types.items():
            percentage = count / total_edges * 100 if total_edges > 0 else 0
            logger.info(f"   {edge_type}: {count} ({percentage:.1f}%)")
        
        return analysis
        
    except Exception as e:
        logger.error(f"图质量分析失败: {e}")
        return {}

def main():
    """主函数"""
    print("🕸️ 工具关系图构建器")
    print("=" * 50)
    
    # 设置日志
    logger = setup_graph_logger()
    
    try:
        # 验证环境
        if not validate_environment(logger):
            return 1
        
        # 查找embedding文件
        embedding_file = find_latest_embedding_file(logger)
        
        # 加载工具数据
        tools = load_tools_with_embeddings(embedding_file, logger)
        
        # 构建工具图
        graph_stats, graph_module = build_tool_graph(tools, logger)
        
        # 测试图功能
        test_results = test_graph_functionality(graph_module, logger)
        
        # 分析图质量
        analysis = analyze_graph_quality(graph_stats, graph_module, logger)
        
        # 最终总结
        logger.info("=" * 60)
        logger.info("🎉 工具关系图构建完成！")
        logger.info(f"📊 分析报告: {analysis}")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"工具图构建过程失败: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)