"""
工具嵌入向量计算模块
用于计算工具描述的embedding向量，并存储到工具的metadata中
"""

import os
import json
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI
from core.base_module import BaseModule
from core.exceptions import ToolDesignError
from utils.file_manager import FileManager
from utils.data_processor import DataProcessor


class ToolEmbedding(BaseModule):
    """工具嵌入向量计算器"""
    
    def __init__(self, config: Dict[str, Any] = None, logger: logging.Logger = None):
        """
        初始化工具嵌入向量计算器
        
        Args:
            config: 配置字典
            logger: 日志器
        """
        super().__init__(config, logger)
        
        self.openai_client = None
        self.file_manager = None
        self.data_processor = None
        self.similarity_threshold = 0.9
        self.batch_size = 10  # API一次最多请求10个
        self.embedding_model = "text-embedding-v4"
        self.embedding_dimensions = 256
        
    def _setup(self):
        """设置组件"""
        from config.settings import settings
        
        # 初始化OpenAI客户端
        self.openai_client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        
        # 初始化文件管理器
        data_path = settings.get_data_path('tools')
        self.file_manager = FileManager(data_path, self.logger)
        
        # 初始化数据处理器
        self.data_processor = DataProcessor(self.logger)
    
    def process(self, input_data: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
        """
        为工具数据添加embedding向量
        
        Args:
            input_data: 包含工具数据文件路径的字典
            **kwargs: 其他参数
            
        Returns:
            更新后的工具列表
        """
        try:
            file_path = input_data.get('tools_file_path')
            if not file_path:
                # 使用默认的工具文件
                file_path = self._find_latest_tools_file()
            
            if not file_path:
                raise ToolDesignError("No tools file found")
            
            # 加载工具数据
            tools = self._load_tools_data(file_path)
            
            # 计算embedding
            updated_tools = self._add_embeddings_to_tools(tools)
            
            # 保存更新后的工具数据
            self._save_tools_with_embeddings(updated_tools)
            
            self.logger.info(f"Successfully added embeddings to {len(updated_tools)} tools")
            return updated_tools
            
        except Exception as e:
            self.logger.error(f"Tool embedding processing failed: {e}")
            raise ToolDesignError(f"Failed to process tool embeddings: {e}")
    
    def _find_latest_tools_file(self) -> Optional[str]:
        """查找最新的工具文件"""
        try:
            tool_files = self.file_manager.list_files(".", "*tools_refined*.json")
            if not tool_files:
                tool_files = self.file_manager.list_files(".", "*tools_batch*.json")
            
            if tool_files:
                # 按时间排序，返回最新的
                return sorted(tool_files)[-1]
            return None
        except Exception as e:
            self.logger.error(f"Failed to find tools file: {e}")
            return None
    
    def _load_tools_data(self, file_path: str) -> List[Dict[str, Any]]:
        """加载工具数据"""
        try:
            return self.file_manager.load_json(file_path)
        except Exception as e:
            self.logger.error(f"Failed to load tools data: {e}")
            raise ToolDesignError(f"Failed to load tools data: {e}")
    
    def _add_embeddings_to_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """为工具添加embedding向量"""
        try:
            # 提取所有需要计算embedding的描述文本
            descriptions = [tool.get('description', '') for tool in tools]
            
            self.logger.info(f"Computing embeddings for {len(descriptions)} tools")
            
            # 批量计算embedding
            embeddings = self.get_embeddings(descriptions)
            
            # 将embedding添加到工具的metadata中
            updated_tools = []
            for i, tool in enumerate(tools):
                updated_tool = tool.copy()
                if 'metadata' not in updated_tool:
                    updated_tool['metadata'] = {}
                
                updated_tool['metadata']['embedding'] = embeddings[i] if i < len(embeddings) else None
                updated_tool['metadata']['embedding_model'] = self.embedding_model
                updated_tool['metadata']['embedding_updated_at'] = datetime.now().isoformat()
                
                updated_tools.append(updated_tool)
            
            return updated_tools
            
        except Exception as e:
            self.logger.error(f"Failed to add embeddings to tools: {e}")
            raise ToolDesignError(f"Failed to add embeddings: {e}")
    
    def get_embeddings(self, strings: List[str]) -> List[List[float]]:
        """
        获取字符串的embedding向量
        
        Args:
            strings: 字符串列表
            
        Returns:
            embedding向量列表
        """
        all_embeddings = []
        
        # 分批处理
        for i in range(0, len(strings), self.batch_size):
            batch = strings[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(strings) + self.batch_size - 1) // self.batch_size
            
            self.logger.info(f"Processing embedding batch {batch_num}/{total_batches}")
            
            try:
                response = self.openai_client.embeddings.create(
                    model=self.embedding_model,
                    input=batch,
                    dimensions=self.embedding_dimensions,
                    encoding_format="float"
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                
            except Exception as e:
                self.logger.error(f"Error processing embedding batch {batch_num}: {e}")
                # 为失败的批次填充零向量
                batch_embeddings = [[0.0] * self.embedding_dimensions for _ in batch]
                all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
    
    def _save_tools_with_embeddings(self, tools: List[Dict[str, Any]]):
        """保存包含embedding的工具数据"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tools_with_embeddings_{timestamp}.json"
            
            self.file_manager.save_json(tools, filename)
            
            # 保存汇总信息
            summary = {
                'total_tools': len(tools),
                'embedding_model': self.embedding_model,
                'embedding_dimensions': self.embedding_dimensions,
                'processed_at': timestamp,
                'has_embedding_count': len([t for t in tools if t.get('metadata', {}).get('embedding')])
            }
            
            summary_filename = f"embeddings_summary_{timestamp}.json"
            self.file_manager.save_json(summary, summary_filename)
            
            self.logger.info(f"Saved tools with embeddings to {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to save tools with embeddings: {e}")
            raise ToolDesignError(f"Failed to save tools: {e}")