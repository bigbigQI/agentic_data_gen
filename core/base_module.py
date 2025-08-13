"""
模块基类定义
所有业务模块的基类，提供通用功能
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from .exceptions import AgentDataGenException


class BaseModule(ABC):
    """
    所有业务模块的基类
    提供通用的功能和接口
    """
    
    def __init__(self, config: Dict[str, Any] = None, logger: logging.Logger = None):
        """
        初始化基础模块
        
        Args:
            config: 模块配置
            logger: 日志器实例
        """
        self.config = config or {}
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.metadata = {
            "module_name": self.__class__.__name__,
            "created_at": datetime.now(),
            "version": "1.0.0"
        }
        self._initialized = False
        
    def initialize(self) -> None:
        """
        初始化模块
        子类可以重写此方法进行特定的初始化逻辑
        """
        try:
            self._setup()
            self._initialized = True
            self.logger.info(f"{self.__class__.__name__} initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.__class__.__name__}: {e}")
            raise AgentDataGenException(f"Module initialization failed: {e}")
    
    def _setup(self) -> None:
        """
        子类特定的设置逻辑
        子类应该重写此方法
        """
        pass
    
    # @abstractmethod
    def process(self, input_data: Any, **kwargs) -> Any:
        """
        处理输入数据的主要方法
        所有子类必须实现此方法
        
        Args:
            input_data: 输入数据
            **kwargs: 额外的关键字参数
            
        Returns:
            处理后的数据
        """
        pass
    
    def validate_input(self, input_data: Any) -> bool:
        """
        验证输入数据
        子类可以重写此方法进行特定的验证
        
        Args:
            input_data: 要验证的输入数据
            
        Returns:
            验证是否通过
        """
        return input_data is not None
    
    def validate_output(self, output_data: Any) -> bool:
        """
        验证输出数据
        子类可以重写此方法进行特定的验证
        
        Args:
            output_data: 要验证的输出数据
            
        Returns:
            验证是否通过
        """
        return output_data is not None
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取模块状态
        
        Returns:
            模块状态信息
        """
        return {
            "module_name": self.__class__.__name__,
            "initialized": self._initialized,
            "metadata": self.metadata,
            "config": self.config
        }
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        更新模块配置
        
        Args:
            new_config: 新的配置
        """
        self.config.update(new_config)
        self.logger.info(f"Config updated for {self.__class__.__name__}")
    
    def cleanup(self) -> None:
        """
        清理资源
        子类可以重写此方法进行特定的清理逻辑
        """
        self.logger.info(f"Cleaning up {self.__class__.__name__}")
    
    def __enter__(self):
        """上下文管理器入口"""
        if not self._initialized:
            self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.cleanup() 