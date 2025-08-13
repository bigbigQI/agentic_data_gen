#!/usr/bin/env python3
"""
工具过滤脚本
根据质量评估结果过滤低质量工具，并基于embedding相似度去重
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple
from collections import defaultdict

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from utils.logger import setup_logger
from utils.file_manager import FileManager


def setup_filter_logger():
    """设置工具过滤专用日志器"""
    logger = setup_logger(
        "tool_filter",
        level=settings.LOGGING_CONFIG["level"],
        log_file=settings.LOGGING_CONFIG["file_path"]
    )
    return logger


def validate_environment():
    """验证环境配置"""
    required_files = []
    
    # 检查必需的环境变量
    if not os.getenv('OPENAI_API_KEY') and not os.getenv('DASHSCOPE_API_KEY'):
        print("❌ 缺少API密钥，需要设置 OPENAI_API_KEY 或 DASHSCOPE_API_KEY")
        return False
    
    print("✅ 环境变量检查通过")
    return True


def find_latest_files():
    """查找最新的工具文件和评估文件"""
    tools_dir = settings.get_data_path('tools')
    file_manager = FileManager(tools_dir)
    
    # 查找工具文件（优先选择带embedding的文件）
    embedding_files = file_manager.list_files(".", "*tools_with_embeddings*.json")
    tools_file = None
    if embedding_files:
        tools_file = max(embedding_files, key=lambda f: file_manager.get_file_info(f)['modified'])
    
    # 查找评估文件
    evaluation_files = file_manager.list_files(".", "*tool_evaluations*.json")
    evaluation_file = None
    if evaluation_files:
        evaluation_file = max(evaluation_files, key=lambda f: file_manager.get_file_info(f)['modified'])
    
    return tools_file, evaluation_file


def load_data_files(tools_file: str, evaluation_file: str):
    """加载工具和评估数据文件"""
    tools_dir = settings.get_data_path('tools')
    file_manager = FileManager(tools_dir)
    
    # 加载工具数据
    if not tools_file:
        raise FileNotFoundError("未找到工具数据文件")
    
    print(f"📂 加载工具数据: {os.path.basename(tools_file)}")
    tools_data = file_manager.load_json(os.path.basename(tools_file))
    print(f"✅ 成功加载 {len(tools_data)} 个工具")
    
    # 加载评估数据
    evaluations_data = []
    if evaluation_file:
        print(f"📂 加载评估数据: {os.path.basename(evaluation_file)}")
        evaluations_data = file_manager.load_json(os.path.basename(evaluation_file))
        print(f"✅ 成功加载 {len(evaluations_data)} 个评估结果")
    else:
        print("⚠️  未找到评估文件，将跳过质量过滤步骤")
    
    return tools_data, evaluations_data


def filter_tools_by_quality(tools_data: List[Dict], evaluations_data: List[Dict], 
                           quality_threshold: float = 4.0) -> Tuple[List[Dict], Dict]:
    """根据质量评估结果过滤工具"""
    if not evaluations_data:
        print("📊 跳过质量过滤步骤")
        return tools_data, {'skipped': True}
    
    print(f"🔍 根据质量阈值 {quality_threshold} 过滤工具...")
    
    # 创建评估结果映射
    evaluation_map = {}
    for eval_item in evaluations_data:
        tool_id = eval_item.get('tool_id')
        total_score = eval_item.get('overall_score', 0)
        if tool_id:
            evaluation_map[tool_id] = total_score
    
    # 过滤高质量工具
    high_quality_tools = []
    quality_stats = {
        'total_tools': len(tools_data),
        'evaluated_tools': 0,
        'high_quality_tools': 0,
        'filtered_out': 0,
        'no_evaluation': 0
    }
    
    for tool in tools_data:
        tool_id = tool.get('id')
        
        if tool_id in evaluation_map:
            quality_stats['evaluated_tools'] += 1
            score = evaluation_map[tool_id]
            
            if score >= quality_threshold:
                high_quality_tools.append(tool)
                quality_stats['high_quality_tools'] += 1
            else:
                quality_stats['filtered_out'] += 1
        else:
            # 没有评估的工具默认保留
            high_quality_tools.append(tool)
            quality_stats['no_evaluation'] += 1
    
    print(f"📈 质量过滤结果:")
    print(f"  总工具数: {quality_stats['total_tools']}")
    print(f"  有评估的工具: {quality_stats['evaluated_tools']}")
    print(f"  高质量工具: {quality_stats['high_quality_tools']}")
    print(f"  被过滤的工具: {quality_stats['filtered_out']}")
    print(f"  无评估工具: {quality_stats['no_evaluation']}")
    
    return high_quality_tools, quality_stats


def calculate_cosine_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """计算两个embedding向量的余弦相似度"""
    try:
        if not embedding1 or not embedding2:
            return 0.0
        
        if len(embedding1) != len(embedding2):
            return 0.0
        
        # 手动计算余弦相似度，避免依赖sklearn
        import math
        
        # 计算点积
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        
        # 计算向量长度
        norm_a = math.sqrt(sum(a * a for a in embedding1))
        norm_b = math.sqrt(sum(b * b for b in embedding2))
        
        # 避免除零
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        # 计算余弦相似度
        similarity = dot_product / (norm_a * norm_b)
        return float(max(0.0, min(1.0, similarity)))  # 确保结果在[0,1]范围内
        
    except Exception:
        return 0.0


def group_tools_by_scenario(tools_data: List[Dict]) -> Dict[str, List[Dict]]:
    """将工具按场景分组"""
    scenario_groups = defaultdict(list)
    
    for tool in tools_data:
        scenario_ids = tool.get('scenario_ids', [])
        
        if scenario_ids:
            # 取第一个scenario作为主场景
            primary_scenario = scenario_ids[0]
            scenario_groups[primary_scenario].append(tool)
        else:
            # 没有场景的工具单独分组
            scenario_groups['no_scenario'].append(tool)
    
    return scenario_groups


def deduplicate_tools_in_scenario(tools_in_scenario: List[Dict], 
                                similarity_threshold: float = 0.8) -> Tuple[List[Dict], Dict]:
    """在场景内基于embedding相似度去重"""
    if len(tools_in_scenario) <= 1:
        return tools_in_scenario, {'clusters': 0, 'removed': 0}
    
    # 过滤有embedding的工具
    tools_with_embedding = []
    tools_without_embedding = []
    
    for tool in tools_in_scenario:
        embedding = tool.get('metadata', {}).get('embedding')
        if embedding and any(x != 0.0 for x in embedding):
            tools_with_embedding.append(tool)
        else:
            tools_without_embedding.append(tool)
    
    # 如果没有embedding，直接返回
    if len(tools_with_embedding) <= 1:
        return tools_in_scenario, {'clusters': 0, 'removed': 0}
    
    # 计算相似度矩阵并聚类
    clusters = []
    used_indices = set()
    
    for i, tool1 in enumerate(tools_with_embedding):
        if i in used_indices:
            continue
        
        # 创建新簇
        cluster = [i]
        embedding1 = tool1['metadata']['embedding']
        
        # 寻找相似的工具
        for j, tool2 in enumerate(tools_with_embedding[i+1:], i+1):
            if j in used_indices:
                continue
            
            embedding2 = tool2['metadata']['embedding']
            similarity = calculate_cosine_similarity(embedding1, embedding2)
            
            if similarity >= similarity_threshold:
                cluster.append(j)
                used_indices.add(j)
        
        clusters.append(cluster)
        used_indices.add(i)
    
    # 从每个簇中选择最佳工具
    selected_tools = []
    removed_count = 0
    
    for cluster in clusters:
        if len(cluster) == 1:
            # 单独的工具直接保留
            selected_tools.append(tools_with_embedding[cluster[0]])
        else:
            # 从簇中选择最佳工具（这里选择第一个，可以根据其他标准优化）
            best_tool = tools_with_embedding[cluster[0]]
            selected_tools.append(best_tool)
            removed_count += len(cluster) - 1
    
    # 添加没有embedding的工具
    selected_tools.extend(tools_without_embedding)
    
    dedup_stats = {
        'clusters': len(clusters),
        'removed': removed_count,
        'original_count': len(tools_in_scenario),
        'final_count': len(selected_tools)
    }
    
    return selected_tools, dedup_stats


def filter_duplicate_tools(tools_data: List[Dict], similarity_threshold: float = 0.85) -> Tuple[List[Dict], Dict]:
    """基于embedding相似度在各场景内去重"""
    print(f"🔄 基于embedding相似度去重 (阈值: {similarity_threshold})...")
    
    # 按场景分组
    scenario_groups = group_tools_by_scenario(tools_data)
    print(f"📊 发现 {len(scenario_groups)} 个场景分组")
    
    # 在每个场景内去重
    final_tools = []
    total_stats = {
        'total_scenarios': len(scenario_groups),
        'total_clusters': 0,
        'total_removed': 0,
        'original_total': len(tools_data),
        'scenario_details': {}
    }
    
    for scenario_id, tools_in_scenario in scenario_groups.items():
        if len(tools_in_scenario) > 1:
            deduplicated_tools, dedup_stats = deduplicate_tools_in_scenario(
                tools_in_scenario, similarity_threshold
            )
            
            final_tools.extend(deduplicated_tools)
            total_stats['total_clusters'] += dedup_stats['clusters']
            total_stats['total_removed'] += dedup_stats['removed']
            total_stats['scenario_details'][scenario_id] = dedup_stats
            
            if dedup_stats['removed'] > 0:
                print(f"  场景 {scenario_id}: {dedup_stats['original_count']} → {dedup_stats['final_count']} "
                      f"(-{dedup_stats['removed']})")
        else:
            final_tools.extend(tools_in_scenario)
            total_stats['scenario_details'][scenario_id] = {
                'clusters': 0, 'removed': 0, 
                'original_count': len(tools_in_scenario),
                'final_count': len(tools_in_scenario)
            }
    
    total_stats['final_total'] = len(final_tools)
    
    print(f"📈 去重结果:")
    print(f"  原始工具数: {total_stats['original_total']}")
    print(f"  最终工具数: {total_stats['final_total']}")
    print(f"  移除工具数: {total_stats['total_removed']}")
    
    return final_tools, total_stats


def save_filtered_tools(tools_data: List[Dict], quality_stats: Dict, dedup_stats: Dict):
    """保存过滤后的工具"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tools_dir = settings.get_data_path('tools')
    file_manager = FileManager(tools_dir)
    
    # 保存最终工具数据
    final_tools_file = f"final_tools_{timestamp}.json"
    file_manager.save_json(tools_data, final_tools_file)
    print(f"💾 最终工具数据已保存: {final_tools_file}")
    
    # 保存过滤统计报告
    filter_report = {
        'filter_summary': {
            'timestamp': timestamp,
            'final_tool_count': len(tools_data),
            'quality_filter_applied': not quality_stats.get('skipped', False),
            'similarity_deduplication_applied': True
        },
        'quality_filter_stats': quality_stats,
        'deduplication_stats': dedup_stats,
        'process_metadata': {
            'similarity_threshold': 0.8,
            'quality_threshold': 4.0,
            'processed_at': datetime.now().isoformat()
        }
    }
    
    report_file = f"filter_report_{timestamp}.json"
    file_manager.save_json(filter_report, report_file)
    print(f"💾 过滤报告已保存: {report_file}")
    
    return final_tools_file, report_file


def main():
    """主函数"""
    print("🔧 工具过滤器")
    print("="*60)
    
    # 验证环境
    if not validate_environment():
        return
    
    # 设置日志
    logger = setup_filter_logger()
    
    try:
        # 1. 查找最新文件
        print("🔍 查找最新的工具和评估文件...")
        tools_file, evaluation_file = find_latest_files()
        
        if not tools_file:
            print("❌ 未找到工具数据文件")
            return
        
        # 2. 加载数据
        tools_data, evaluations_data = load_data_files(tools_file, evaluation_file)
        
        # 3. 质量过滤
        filtered_tools, quality_stats = filter_tools_by_quality(
            tools_data, evaluations_data, quality_threshold=4.0
        )
        
        # 4. 相似度去重
        final_tools, dedup_stats = filter_duplicate_tools(
            filtered_tools, similarity_threshold=0.85
        )
        
        # 5. 保存结果
        print(f"\n💾 保存过滤结果...")
        final_file, report_file = save_filtered_tools(final_tools, quality_stats, dedup_stats)
        
        print(f"\n✅ 工具过滤完成！")
        print(f"📁 结果文件:")
        print(f"  - 最终工具: {final_file}")
        print(f"  - 过滤报告: {report_file}")
        
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断执行")
    except Exception as e:
        logger.error(f"工具过滤失败: {e}")
        print(f"❌ 过滤失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
