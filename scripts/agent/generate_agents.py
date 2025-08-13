#!/usr/bin/env python3
"""
智能体生成脚本
基于工具数据生成多样化的智能体配置
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
from modules.agent_synthesizer import AgentSynthesizerModule
from utils.logger import setup_logger
from utils.file_manager import FileManager


def setup_agent_logger():
    """设置智能体生成专用日志器"""
    logger = setup_logger(
        "agent_generation",
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


def find_latest_tools_file():
    """查找最新的工具文件"""
    tools_dir = settings.get_data_path('tools')
    file_manager = FileManager(tools_dir)
    
    # 优先查找最终过滤后的工具文件
    final_files = file_manager.list_files(".", "*final_tools*.json")
    if final_files:
        latest_file = max(final_files, key=lambda f: file_manager.get_file_info(f)['modified'])
        return os.path.join(tools_dir, latest_file)
    
    return None


def load_tools_data(file_path: str):
    """加载工具数据"""
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return []
    
    print(f"📂 加载工具数据: {os.path.basename(file_path)}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        tools_data = json.load(f)
    
    print(f"✅ 成功加载 {len(tools_data)} 个工具")
    
    return tools_data

def main():
    """主函数"""
    print("🤖 智能体生成器")
    print("="*60)
    
    # 验证环境
    if not validate_environment():
        return
    
    # 设置日志
    logger = setup_agent_logger()
    
    try:
        # 1. 自动查找最新工具文件
        tools_file = find_latest_tools_file()
        if not tools_file:
            print("❌ 未找到工具数据文件")
            return
        
        # 2. 加载工具数据
        tools_data = load_tools_data(tools_file)
        if not tools_data:
            print("❌ 无法加载工具数据，程序退出")
            return
        
        # 4. 获取配置
        agent_config = settings.GENERATION_CONFIG.get('agents', {})
        target_count = agent_config.get('target_count', 1000)
        
        print(f"\n🎯 生成配置:")
        print(f"  目标智能体数量: {target_count}")
        print(f"  工具总数: {len(tools_data)}")
        
        tools_per_agent = agent_config.get('tools_per_agent', {})
        min_tools = tools_per_agent.get('min', 3)
        max_tools = tools_per_agent.get('max', 6)
        print(f"  每个智能体工具数量: {min_tools}-{max_tools} 个")
        
        # 5. 初始化智能体合成模块
        print("\n⚙️ 初始化智能体合成模块...")
        synthesizer = AgentSynthesizerModule(logger=logger)
        synthesizer.initialize()
        
        # 6. 生成智能体配置
        print("\n🔄 开始智能体合成...")
        
        start_time = datetime.now()
        
        result = synthesizer.process({
            'tools': tools_data,
            'target_agent_count': target_count
        })
        
        end_time = datetime.now()
        generation_time = (end_time - start_time).total_seconds()
        
        print(f"\n⏱️ 生成耗时: {generation_time:.2f} 秒")
        print(f"📊 生成速度: {len(result.get('agents', []))/generation_time:.1f} 智能体/秒")
        
        
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断执行")
    except Exception as e:
        logger.error(f"智能体生成失败: {e}")
        print(f"❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
