#!/usr/bin/env python3
"""
训练数据转换脚本

将高质量轨迹数据转换为标准训练数据格式
"""

import os
import sys
import json
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from utils.logger import setup_logger
from utils.file_manager import FileManager


def setup_conversion_logger():
    """设置数据转换专用日志器"""
    logger = setup_logger(
        "training_data_conversion",
        level=settings.LOGGING_CONFIG["level"],
        log_file=settings.LOGGING_CONFIG["file_path"]
    )
    return logger


def load_high_quality_trajectories(source_dir: Path, logger: logging.Logger) -> List[Dict[str, Any]]:
    """
    加载高质量轨迹数据
    
    Args:
        source_dir: 高质量轨迹目录
        logger: 日志器
        
    Returns:
        轨迹数据列表
    """
    logger.info(f"开始加载高质量轨迹数据: {source_dir}")
    
    if not source_dir.exists():
        logger.error(f"源目录不存在: {source_dir}")
        return []
    
    # 查找所有JSON文件
    json_files = list(source_dir.glob("*.json"))
    logger.info(f"找到 {len(json_files)} 个高质量轨迹文件")
    
    trajectories = []
    failed_count = 0
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, dict):
                data['_source_file'] = json_file.name
                trajectories.append(data)
            else:
                logger.warning(f"跳过无效格式文件: {json_file.name}")
                failed_count += 1
                
        except Exception as e:
            logger.error(f"加载文件失败 {json_file.name}: {e}")
            failed_count += 1
    
    logger.info(f"成功加载 {len(trajectories)} 个轨迹，失败 {failed_count} 个")
    return trajectories


def load_agents_data(logger: logging.Logger) -> Dict[str, Any]:
    """
    加载智能体数据
    
    Args:
        logger: 日志器
        
    Returns:
        智能体数据字典 {agent_id: agent_data}
    """
    try:
        agents_dir = settings.get_data_path('agents')
        
        if not agents_dir.exists():
            logger.warning(f"智能体目录不存在: {agents_dir}")
            return {}
        
        # 查找最新的智能体文件
        agents_files = list(agents_dir.glob('agents_batch_*.json'))
        
        if not agents_files:
            logger.warning("没有找到智能体数据文件")
            return {}
        
        # 使用最新的文件
        latest_file = max(agents_files, key=lambda f: f.stat().st_mtime)
        logger.info(f"加载智能体数据: {latest_file.name}")
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            agents_list = json.load(f)
        
        # 转换为字典格式
        agents_dict = {}
        for agent in agents_list:
            if isinstance(agent, dict) and 'id' in agent:
                agents_dict[agent['id']] = agent
        
        logger.info(f"成功加载 {len(agents_dict)} 个智能体")
        return agents_dict
        
    except Exception as e:
        logger.error(f"加载智能体数据失败: {e}")
        return {}


def load_tools_data(logger: logging.Logger) -> Dict[str, Any]:
    """
    加载工具数据
    
    Args:
        logger: 日志器
        
    Returns:
        工具数据字典 {tool_id: tool_data}
    """
    try:
        tools_dir = settings.get_data_path('tools')
        
        if not tools_dir.exists():
            logger.warning(f"工具目录不存在: {tools_dir}")
            return {}
        
        # 查找工具数据文件
        tool_files = list(tools_dir.glob('final_tools_*.json'))
        
        if not tool_files:
            logger.warning("没有找到工具数据文件")
            return {}
        
        # 使用最新的文件
        latest_file = max(tool_files, key=lambda f: f.stat().st_mtime)
        logger.info(f"加载工具数据: {latest_file.name}")
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            tools_data = json.load(f)
        
        # 处理不同的数据格式
        tools_dict = {}
        if isinstance(tools_data, list):
            # 如果是列表格式，转换为字典
            for tool in tools_data:
                if isinstance(tool, dict) and 'id' in tool:
                    tools_dict[tool['id']] = tool
        elif isinstance(tools_data, dict):
            tools_dict = tools_data
        
        logger.info(f"成功加载 {len(tools_dict)} 个工具")
        return tools_dict
        
    except Exception as e:
        logger.error(f"加载工具数据失败: {e}")
        return {}


def extract_tools_info(
    trajectory_data: Dict[str, Any], 
    agents_data: Dict[str, Any], 
    tools_data: Dict[str, Any],
    logger: logging.Logger
) -> str:
    """
    从轨迹数据中提取工具信息
    
    Args:
        trajectory_data: 轨迹数据
        agents_data: 智能体数据
        tools_data: 工具数据
        logger: 日志器
        
    Returns:
        工具描述JSON字符串
    """
    try:
        # 1. 从轨迹中获取agent_id
        agent_id = trajectory_data.get('agent_id', '')
        
        if not agent_id:
            logger.warning(f"轨迹 {trajectory_data.get('trajectory_id', 'unknown')} 没有agent_id")
            return "[]"
        
        # 2. 找到对应的agent数据
        if agent_id not in agents_data:
            logger.warning(f"找不到agent数据: {agent_id}")
            return "[]"
        
        agent_data = agents_data[agent_id]
        
        # 3. 获取agent的available tools (tool ids)
        agent_tools = agent_data.get('tools', [])
        
        if not agent_tools:
            logger.warning(f"Agent {agent_id} 没有配置工具")
            return "[]"
        
        # 4. 从tools数据中根据tool_id获取工具描述
        tools_info = []
        
        for tool_id in agent_tools:
            if tool_id in tools_data:
                tool_data = tools_data[tool_id]
                
                # 转换为标准格式
                tool_description = {
                    "name": tool_data.get('name', tool_id),
                    "description": tool_data.get('description', f"Tool {tool_id}"),
                    "parameters": tool_data.get('parameters', {
                        "type": "object",
                        "properties": {},
                        "required": []
                    })
                }
                
                tools_info.append(tool_description)
            else:
                logger.warning(f"找不到工具数据: {tool_id}")
        
        return json.dumps(tools_info, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"提取工具信息失败: {e}")
        return "[]"


def extract_json_from_content(content: str) -> str:
    """
    从内容中提取纯JSON字符串（参考tool_execution_simulator.py的逻辑）
    
    Args:
        content: 原始内容字符串
        
    Returns:
        提取的纯JSON字符串
    """
    import re
    
    def find_balanced_json(text: str, start_pos: int = 0) -> tuple:
        """
        从指定位置开始查找平衡的JSON对象
        返回 (json_str, end_pos) 或 (None, -1)
        """
        brace_count = 0
        in_string = False
        escape_next = False
        start_brace_pos = -1
        
        i = start_pos
        while i < len(text):
            char = text[i]
            
            if escape_next:
                escape_next = False
                i += 1
                continue
                
            if char == '\\' and in_string:
                escape_next = True
                i += 1
                continue
                
            if char == '"':
                in_string = not in_string
                i += 1
                continue
                
            if not in_string:
                if char == '{':
                    if start_brace_pos == -1:
                        start_brace_pos = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_brace_pos != -1:
                        json_candidate = text[start_brace_pos:i+1]
                        try:
                            json.loads(json_candidate)
                            return json_candidate, i+1
                        except json.JSONDecodeError:
                            # 重置并继续查找
                            brace_count = 0
                            start_brace_pos = -1
                            
            i += 1
                            
        return None, -1
    
    try:
        content_str = str(content).strip()
        
        # 如果内容为空，直接返回
        if not content_str:
            return content_str
        
        processed_json_strings = set()
        extracted_json = None
        
        # 1. 提取 ```json ... ``` 代码块
        json_code_pattern = r'```json\s*(.*?)\s*```'
        matches = re.findall(json_code_pattern, content_str, re.DOTALL)
        for match in matches:
            json_content = match.strip()
            if json_content and json_content not in processed_json_strings:
                processed_json_strings.add(json_content)
                try:
                    # 验证是否为有效JSON
                    json.loads(json_content)
                    extracted_json = json_content
                    break
                except json.JSONDecodeError:
                    continue
        
        # 2. 如果没找到，提取 ``` ... ``` 代码块（无语言标识）
        if not extracted_json:
            code_block_pattern = r'```\s*(.*?)\s*```'
            matches_code = re.findall(code_block_pattern, content_str, re.DOTALL)
            for match in matches_code:
                code_content = match.strip()
                if code_content and code_content not in processed_json_strings:
                    processed_json_strings.add(code_content)
                    try:
                        # 验证是否为有效JSON
                        json.loads(code_content)
                        extracted_json = code_content
                        break
                    except json.JSONDecodeError:
                        continue
        
        # 3. 如果还没找到，尝试解析整个内容作为JSON字符串（适用于纯JSON格式）
        if not extracted_json:
            # 移除所有代码块后的内容
            remaining_content = content_str
            remaining_content = re.sub(r'```json.*?```', ' ', remaining_content, flags=re.DOTALL)
            remaining_content = re.sub(r'```.*?```', ' ', remaining_content, flags=re.DOTALL)
            remaining_content = remaining_content.strip()
            
            # 直接尝试解析整个内容
            if remaining_content and remaining_content not in processed_json_strings:
                try:
                    # 验证是否为有效JSON
                    json.loads(remaining_content)
                    extracted_json = remaining_content
                except json.JSONDecodeError:
                    pass
        
        # 4. 如果还没找到，使用平衡查找方式寻找JSON对象
        if not extracted_json:
            remaining_content = content_str
            # 移除所有代码块
            remaining_content = re.sub(r'```json.*?```', ' ', remaining_content, flags=re.DOTALL)
            remaining_content = re.sub(r'```.*?```', ' ', remaining_content, flags=re.DOTALL)
            
            # 查找第一个完整的JSON对象
            pos = 0
            while pos < len(remaining_content):
                json_candidate, next_pos = find_balanced_json(remaining_content, pos)
                if json_candidate and json_candidate not in processed_json_strings:
                    processed_json_strings.add(json_candidate)
                    # 验证JSON是否包含name字段（优先选择包含name的JSON）
                    try:
                        parsed = json.loads(json_candidate)
                        if isinstance(parsed, dict) and 'name' in parsed:
                            extracted_json = json_candidate
                            break
                        elif not extracted_json:  # 如果还没找到任何JSON，保存当前这个
                            extracted_json = json_candidate
                    except json.JSONDecodeError:
                        pass
                    pos = next_pos
                else:
                    pos += 1
        
        # 如果找到了提取的JSON，返回它，否则返回原内容
        return extracted_json if extracted_json else content_str
        
    except Exception as e:
        # 如果处理过程中出错，返回原内容
        return str(content)


def convert_trajectory_to_training_format(
    trajectory_data: Dict[str, Any], 
    agents_data: Dict[str, Any], 
    tools_data: Dict[str, Any],
    logger: logging.Logger
) -> Optional[Dict[str, Any]]:
    """
    将单个轨迹转换为训练数据格式
    
    Args:
        trajectory_data: 轨迹数据
        agents_data: 智能体数据
        tools_data: 工具数据
        logger: 日志器
        
    Returns:
        转换后的训练数据
    """
    try:
        # 提取消息列表
        messages = trajectory_data.get('messages', [])
        if not messages:
            logger.warning(f"轨迹 {trajectory_data.get('trajectory_id', 'unknown')} 没有消息数据")
            return None
        
        # 移除最后一条human消息（不需要训练）
        if messages and messages[-1].get('role') == 'user':
            messages = messages[:-1]
            logger.debug(f"移除最后一条human消息: {trajectory_data.get('trajectory_id', 'unknown')}")
        
        conversations = []
        
        for message in messages:
            role = message.get('role', '')
            content = message.get('content', '')
            recipient = message.get('recipient', '')
            
            # 角色映射
            if role == 'user':
                conversations.append({
                    "from": "human",
                    "value": str(content)
                })
            elif role == 'assistant':
                # 检查是否包含工具调用
                content_str = str(content)
                if recipient == 'execution':
                    # 这是一个工具调用，提取纯JSON格式
                    clean_json = extract_json_from_content(content_str)
                    
                    # 验证JSON中是否包含必要的字段
                    try:
                        parsed_json = json.loads(clean_json)
                        if not isinstance(parsed_json, dict):
                            logger.warning(f"轨迹 {trajectory_data.get('trajectory_id', 'unknown')} function_call不是有效的JSON对象")
                            return None
                        
                        # 检查是否包含name和arguments字段
                        if 'name' not in parsed_json or 'arguments' not in parsed_json:
                            logger.warning(f"轨迹 {trajectory_data.get('trajectory_id', 'unknown')} function_call缺少name或arguments字段")
                            return None
                        
                    except json.JSONDecodeError:
                        logger.warning(f"轨迹 {trajectory_data.get('trajectory_id', 'unknown')} function_call不是有效的JSON格式")
                        return None
                    
                    conversations.append({
                        "from": "function_call",
                        "value": clean_json
                    })
                else:
                    # 这是普通的助手回复
                    conversations.append({
                        "from": "gpt",
                        "value": content_str
                    })
            elif role == 'execution':
                # 工具执行结果
                if isinstance(content, list):
                    # 合并多个执行结果
                    observation_content = []
                    for result in content:
                        if isinstance(result, dict):
                            result.pop('metadata')
                            observation_content.append(json.dumps(result, ensure_ascii=False))
                        else:
                            print(result)
                            observation_content.append(str(result))
                    conversations.append({
                        "from": "observation", 
                        "value": "\n".join(observation_content)
                    })
                else:
                    conversations.append({
                        "from": "observation",
                        "value": str(content)
                    })
        
        # 如果没有有效的对话，跳过
        if not conversations:
            logger.warning(f"轨迹 {trajectory_data.get('trajectory_id', 'unknown')} 没有有效对话")
            return None
        
        # 提取工具信息
        tools_info = extract_tools_info(trajectory_data, agents_data, tools_data, logger)
        
        training_item = {
            "conversations": conversations,
            "tools": tools_info
        }
        
        return training_item
        
    except Exception as e:
        logger.error(f"转换轨迹失败 {trajectory_data.get('trajectory_id', 'unknown')}: {e}")
        return None


def convert_trajectories_to_training_data(
    trajectories: List[Dict[str, Any]], 
    agents_data: Dict[str, Any], 
    tools_data: Dict[str, Any],
    logger: logging.Logger
) -> List[Dict[str, Any]]:
    """
    批量转换轨迹为训练数据
    
    Args:
        trajectories: 轨迹数据列表
        agents_data: 智能体数据
        tools_data: 工具数据
        logger: 日志器
        
    Returns:
        训练数据列表
    """
    logger.info(f"开始转换 {len(trajectories)} 个轨迹为训练数据")
    
    training_data = []
    success_count = 0
    failed_count = 0
    
    for i, trajectory in enumerate(trajectories, 1):
        try:
            training_item = convert_trajectory_to_training_format(trajectory, agents_data, tools_data, logger)
            if training_item:
                training_data.append(training_item)
                success_count += 1
            else:
                failed_count += 1
            
            # 进度提示
            if i % 10 == 0:
                logger.info(f"转换进度: {i}/{len(trajectories)} ({i/len(trajectories)*100:.1f}%)")
        
        except Exception as e:
            failed_count += 1
            logger.error(f"转换第 {i} 个轨迹时出错: {e}")
    
    logger.info(f"转换完成: 成功 {success_count} 个，失败 {failed_count} 个")
    return training_data


def save_training_data(
    training_data: List[Dict[str, Any]], 
    target_dir: Path, 
    logger: logging.Logger
) -> str:
    """
    保存训练数据
    
    Args:
        training_data: 训练数据列表
        target_dir: 目标目录
        logger: 日志器
        
    Returns:
        保存的文件路径
    """
    try:
        # 确保目标目录存在
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"training_data_{timestamp}.json"
        
        file_path = target_dir / filename
        
        # 保存数据
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(training_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"训练数据已保存: {file_path}")
        logger.info(f"训练样本总数: {len(training_data)}")
        
        return str(file_path)
        
    except Exception as e:
        logger.error(f"保存训练数据失败: {e}")
        raise


def print_conversion_summary(
    original_count: int, 
    converted_count: int, 
    output_file: str
):
    """打印转换结果摘要"""
    print(f"\n📊 训练数据转换结果")
    print("="*60)
    
    print(f"📈 转换统计:")
    print(f"  原始轨迹数: {original_count}")
    print(f"  成功转换数: {converted_count}")
    print(f"  转换成功率: {converted_count/original_count*100:.1f}%" if original_count > 0 else "  转换成功率: 0.0%")
    
    print(f"\n💾 输出文件:")
    print(f"  文件路径: {output_file}")
    print(f"  训练样本数: {converted_count}")
    
    if converted_count > 0:
        print(f"\n✅ 训练数据已准备完成!")
        print(f"📝 数据格式: 每个样本包含 conversations 和 tools 字段")
        print(f"🔧 对话角色: human, gpt, function_call, observation")
    else:
        print(f"\n❌ 没有成功转换的训练数据")


def main():
    """主函数"""
    print("🔄 训练数据转换器")
    print("="*60)
    
    # 设置日志
    logger = setup_conversion_logger()
    
    try:
        # 1. 设置目录路径
        source_dir = settings.get_data_path('high_quality_trajectories')
        target_dir = settings.get_data_path('training_data')
        
        print(f"📁 源目录: {source_dir}")
        print(f"📁 目标目录: {target_dir}")
        
        # 2. 加载高质量轨迹数据
        print("📂 加载高质量轨迹数据...")
        trajectories = load_high_quality_trajectories(source_dir, logger)
        
        if not trajectories:
            print("❌ 没有找到高质量轨迹数据")
            return 1
        
        print(f"✅ 成功加载 {len(trajectories)} 个高质量轨迹")
        
        # 3. 加载智能体数据
        print("📂 加载智能体数据...")
        agents_data = load_agents_data(logger)
        
        if not agents_data:
            print("⚠️ 没有加载到智能体数据，将使用默认工具配置")
        else:
            print(f"✅ 成功加载 {len(agents_data)} 个智能体")
        
        # 4. 加载工具数据
        print("🔧 加载工具数据...")
        tools_data = load_tools_data(logger)
        
        if not tools_data:
            print("⚠️ 没有加载到工具数据，将使用默认工具定义")
        else:
            print(f"✅ 成功加载 {len(tools_data)} 个工具")
        
        # 5. 转换为训练数据格式
        print("🔄 转换轨迹数据为训练格式...")
        training_data = convert_trajectories_to_training_data(trajectories, agents_data, tools_data, logger)
        
        if not training_data:
            print("❌ 没有成功转换的训练数据")
            return 1
        
        # 6. 保存训练数据
        print("💾 保存训练数据...")
        output_file = save_training_data(training_data, target_dir, logger)
        
        # 7. 显示转换结果摘要
        print_conversion_summary(len(trajectories), len(training_data), output_file)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断执行")
        return 1
    except Exception as e:
        logger.error(f"训练数据转换失败: {e}")
        print(f"❌ 转换失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
