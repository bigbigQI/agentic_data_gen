"""
文件管理工具
处理文件的读写、存储和管理
"""

import json
import pickle
from pathlib import Path
from typing import Any, Dict, List, Union
import logging
from datetime import datetime

from core.exceptions import DataStorageError


class FileManager:
    """文件管理工具类"""
    
    def __init__(self, base_dir: Path = None, logger: logging.Logger = None):
        """
        初始化文件管理器
        
        Args:
            base_dir: 基础目录路径
            logger: 日志器
        """
        self.base_dir = base_dir or Path.cwd()
        self.logger = logger or logging.getLogger(__name__)
    
    def save_json(self, data: Any, file_path: Union[str, Path], indent: int = 2) -> None:
        """
        保存数据为JSON文件
        
        Args:
            data: 要保存的数据
            file_path: 文件路径
            indent: JSON缩进
        """
        try:
            file_path = Path(file_path)
            if not file_path.is_absolute():
                file_path = self.base_dir / file_path
            
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            with file_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=indent, default=str)
            
            self.logger.debug(f"Saved JSON file: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save JSON file {file_path}: {e}")
            raise DataStorageError(f"Failed to save JSON file: {e}")
    
    def load_json(self, file_path: Union[str, Path]) -> Any:
        """
        加载JSON文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            加载的数据
        """
        try:
            file_path = Path(file_path)
            if not file_path.is_absolute():
                file_path = self.base_dir / file_path
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            with file_path.open('r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.logger.debug(f"Loaded JSON file: {file_path}")
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to load JSON file {file_path}: {e}")
            raise DataStorageError(f"Failed to load JSON file: {e}")
    
    def save_pickle(self, data: Any, file_path: Union[str, Path]) -> None:
        """
        保存数据为pickle文件
        
        Args:
            data: 要保存的数据
            file_path: 文件路径
        """
        try:
            file_path = Path(file_path)
            if not file_path.is_absolute():
                file_path = self.base_dir / file_path
            
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            with file_path.open('wb') as f:
                pickle.dump(data, f)
            
            self.logger.debug(f"Saved pickle file: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save pickle file {file_path}: {e}")
            raise DataStorageError(f"Failed to save pickle file: {e}")
    
    def load_pickle(self, file_path: Union[str, Path]) -> Any:
        """
        加载pickle文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            加载的数据
        """
        try:
            file_path = Path(file_path)
            if not file_path.is_absolute():
                file_path = self.base_dir / file_path
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            with file_path.open('rb') as f:
                data = pickle.load(f)
            
            self.logger.debug(f"Loaded pickle file: {file_path}")
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to load pickle file {file_path}: {e}")
            raise DataStorageError(f"Failed to load pickle file: {e}")
    
    def save_text(self, text: str, file_path: Union[str, Path]) -> None:
        """
        保存文本文件
        
        Args:
            text: 文本内容
            file_path: 文件路径
        """
        try:
            file_path = Path(file_path)
            if not file_path.is_absolute():
                file_path = self.base_dir / file_path
            
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            with file_path.open('w', encoding='utf-8') as f:
                f.write(text)
            
            self.logger.debug(f"Saved text file: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save text file {file_path}: {e}")
            raise DataStorageError(f"Failed to save text file: {e}")
    
    def load_text(self, file_path: Union[str, Path]) -> str:
        """
        加载文本文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            文本内容
        """
        try:
            file_path = Path(file_path)
            if not file_path.is_absolute():
                file_path = self.base_dir / file_path
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            with file_path.open('r', encoding='utf-8') as f:
                text = f.read()
            
            self.logger.debug(f"Loaded text file: {file_path}")
            return text
            
        except Exception as e:
            self.logger.error(f"Failed to load text file {file_path}: {e}")
            raise DataStorageError(f"Failed to load text file: {e}")
    
    def list_files(self, directory: Union[str, Path], pattern: str = "*") -> List[Path]:
        """
        列出目录中的文件
        
        Args:
            directory: 目录路径
            pattern: 文件模式
            
        Returns:
            文件路径列表
        """
        try:
            directory = Path(directory)
            if not directory.is_absolute():
                directory = self.base_dir / directory
            
            if not directory.exists():
                return []
            
            files = list(directory.glob(pattern))
            files = [f for f in files if f.is_file()]
            
            self.logger.debug(f"Found {len(files)} files in {directory}")
            return files
            
        except Exception as e:
            self.logger.error(f"Failed to list files in {directory}: {e}")
            raise DataStorageError(f"Failed to list files: {e}")
    
    def ensure_directory(self, directory: Union[str, Path]) -> Path:
        """
        确保目录存在
        
        Args:
            directory: 目录路径
            
        Returns:
            目录路径
        """
        try:
            directory = Path(directory)
            if not directory.is_absolute():
                directory = self.base_dir / directory
            
            directory.mkdir(parents=True, exist_ok=True)
            return directory
            
        except Exception as e:
            self.logger.error(f"Failed to create directory {directory}: {e}")
            raise DataStorageError(f"Failed to create directory: {e}")
    
    def get_file_info(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        获取文件信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件信息字典
        """
        try:
            file_path = Path(file_path)
            if not file_path.is_absolute():
                file_path = self.base_dir / file_path
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            stat = file_path.stat()
            
            return {
                "name": file_path.name,
                "path": str(file_path),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime),
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "is_file": file_path.is_file(),
                "is_directory": file_path.is_dir()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get file info for {file_path}: {e}")
            raise DataStorageError(f"Failed to get file info: {e}")
    
    def delete_file(self, file_path: Union[str, Path]) -> None:
        """
        删除文件
        
        Args:
            file_path: 文件路径
        """
        try:
            file_path = Path(file_path)
            if not file_path.is_absolute():
                file_path = self.base_dir / file_path
            
            if file_path.exists():
                file_path.unlink()
                self.logger.debug(f"Deleted file: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to delete file {file_path}: {e}")
            raise DataStorageError(f"Failed to delete file: {e}")
    
    def copy_file(self, source: Union[str, Path], destination: Union[str, Path]) -> None:
        """
        复制文件
        
        Args:
            source: 源文件路径
            destination: 目标文件路径
        """
        try:
            import shutil
            
            source = Path(source)
            destination = Path(destination)
            
            if not source.is_absolute():
                source = self.base_dir / source
            if not destination.is_absolute():
                destination = self.base_dir / destination
            
            # 确保目标目录存在
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(source, destination)
            self.logger.debug(f"Copied file from {source} to {destination}")
            
        except Exception as e:
            self.logger.error(f"Failed to copy file from {source} to {destination}: {e}")
            raise DataStorageError(f"Failed to copy file: {e}") 