"""
数据处理工具
提供数据转换、验证和处理功能
"""

import json
import hashlib
from typing import List, Dict, Any, Union, Optional
from datetime import datetime
import logging

from core.models import *
from core.exceptions import ModelValidationError


class DataProcessor:
    """数据处理工具类"""
    
    def __init__(self, logger: logging.Logger = None):
        """
        初始化数据处理器
        
        Args:
            logger: 日志器
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def validate_scenario(self, scenario_data: Dict[str, Any]) -> bool:
        """
        验证场景数据
        
        Args:
            scenario_data: 场景数据
            
        Returns:
            验证是否通过
        """
        try:
            required_fields = ['name', 'description', 'context']
            
            for field in required_fields:
                if field not in scenario_data or not scenario_data[field]:
                    raise ModelValidationError(f"Missing required field: {field}")
            
            # 验证描述长度
            if len(scenario_data['description']) < 10:
                raise ModelValidationError("Description too short (minimum 10 characters)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Scenario validation failed: {e}")
            return False
    
    def validate_tool(self, tool_data: Dict[str, Any]) -> bool:
        """
        验证工具数据
        
        Args:
            tool_data: 工具数据
            
        Returns:
            验证是否通过
        """
        try:
            required_fields = ['name', 'description']
            
            for field in required_fields:
                if field not in tool_data or not tool_data[field]:
                    raise ModelValidationError(f"Missing required field: {field}")
            
            # 验证参数
            if 'parameters' in tool_data:
                if not isinstance(tool_data['parameters'], list):
                    raise ModelValidationError("parameters must be a list")
                
                for param in tool_data['parameters']:
                    if not isinstance(param, dict):
                        raise ModelValidationError("Each parameter must be a dict")
                    
                    param_required = ['name', 'type', 'description']
                    for field in param_required:
                        if field not in param:
                            raise ModelValidationError(f"Parameter missing field: {field}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Tool validation failed: {e}")
            return False
    
    def generate_id(self, prefix: str = "", data: Dict[str, Any] = None) -> str:
        """
        生成唯一ID
        
        Args:
            prefix: ID前缀
            data: 用于生成hash的数据
            
        Returns:
            唯一ID
        """
        if data:
            # 基于数据内容生成hash
            data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
            hash_value = hashlib.md5(data_str.encode()).hexdigest()[:8]
            return f"{prefix}_{hash_value}" if prefix else hash_value
        else:
            # 基于时间戳生成ID
            timestamp = int(datetime.now().timestamp() * 1000)
            return f"{prefix}_{timestamp}" if prefix else str(timestamp)
    
    def merge_data_batches(self, batches: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        合并数据批次
        
        Args:
            batches: 数据批次列表
            
        Returns:
            合并后的数据列表
        """
        merged_data = []
        for batch in batches:
            if isinstance(batch, list):
                merged_data.extend(batch)
            else:
                merged_data.append(batch)
        
        self.logger.info(f"Merged {len(batches)} batches into {len(merged_data)} items")
        return merged_data
    
    def filter_by_quality(self, data_list: List[Dict[str, Any]], quality_threshold: float = 3.0) -> List[Dict[str, Any]]:
        """
        按质量过滤数据
        
        Args:
            data_list: 数据列表
            quality_threshold: 质量阈值
            
        Returns:
            过滤后的数据列表
        """
        filtered = []
        
        for item in data_list:
            quality_score = item.get('quality_score', 5.0)  # 默认满分
            
            if quality_score >= quality_threshold:
                filtered.append(item)
        
        self.logger.info(f"Filtered {len(data_list)} items to {len(filtered)} items (threshold: {quality_threshold})")
        return filtered
    
    def convert_to_model(self, data: Dict[str, Any], model_class) -> Any:
        """
        将字典数据转换为数据模型对象
        
        Args:
            data: 字典数据
            model_class: 目标模型类
            
        Returns:
            模型对象
        """
        try:
            # 处理特殊字段
            if 'created_at' in data and isinstance(data['created_at'], str):
                data['created_at'] = datetime.fromisoformat(data['created_at'])
            
            # 处理枚举字段
            if model_class == Task:
                if 'difficulty' in data and isinstance(data['difficulty'], str):
                    data['difficulty'] = DifficultyLevel(data['difficulty'])
                if 'task_type' in data and isinstance(data['task_type'], str):
                    data['task_type'] = TaskType(data['task_type'])
            
            if model_class == UserPersona:
                if 'personality_type' in data and isinstance(data['personality_type'], str):
                    data['personality_type'] = UserPersonalityType(data['personality_type'])
                if 'interaction_style' in data and isinstance(data['interaction_style'], str):
                    data['interaction_style'] = InteractionStyle(data['interaction_style'])
            
            return model_class(**data)
            
        except Exception as e:
            self.logger.error(f"Failed to convert data to {model_class.__name__}: {e}")
            raise ModelValidationError(f"Model conversion failed: {e}")
    
    def convert_model_to_dict(self, model_obj: Any) -> Dict[str, Any]:
        """
        将模型对象转换为字典
        
        Args:
            model_obj: 模型对象
            
        Returns:
            字典数据
        """
        try:
            if hasattr(model_obj, '__dataclass_fields__'):
                data = {}
                for field_name, field_def in model_obj.__dataclass_fields__.items():
                    value = getattr(model_obj, field_name)
                    
                    if isinstance(value, datetime):
                        data[field_name] = value.isoformat()
                    elif isinstance(value, Enum):
                        data[field_name] = value.value
                    elif hasattr(value, '__dataclass_fields__'):
                        data[field_name] = self.convert_model_to_dict(value)
                    elif isinstance(value, list):
                        data[field_name] = [
                            self.convert_model_to_dict(item) if hasattr(item, '__dataclass_fields__') else item 
                            for item in value
                        ]
                    else:
                        data[field_name] = value
                
                return data
            else:
                return model_obj
                
        except Exception as e:
            self.logger.error(f"Failed to convert model to dict: {e}")
            raise ModelValidationError(f"Model conversion failed: {e}")
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            相似度分数 (0-1)
        """
        if not text1 or not text2:
            return 0.0
        
        # 简单的字符级相似度计算
        from difflib import SequenceMatcher
        
        similarity = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
        return similarity
    
    def batch_process(self, data_list: List[Any], processor_func, batch_size: int = 100) -> List[Any]:
        """
        批量处理数据
        
        Args:
            data_list: 数据列表
            processor_func: 处理函数
            batch_size: 批次大小
            
        Returns:
            处理后的数据列表
        """
        results = []
        
        for i in range(0, len(data_list), batch_size):
            batch = data_list[i:i + batch_size]
            try:
                batch_results = processor_func(batch)
                if isinstance(batch_results, list):
                    results.extend(batch_results)
                else:
                    results.append(batch_results)
            except Exception as e:
                self.logger.error(f"Batch processing failed for batch {i//batch_size + 1}: {e}")
                continue
        
        return results 