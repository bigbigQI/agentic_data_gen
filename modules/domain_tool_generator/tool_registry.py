"""
工具注册中心
管理工具的注册、查询和索引
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from core.base_module import BaseModule
from core.models import Tool
from core.exceptions import RegistryError
from utils.data_processor import DataProcessor
from utils.file_manager import FileManager


class ToolRegistry(BaseModule):
    """工具注册中心"""
    
    def __init__(self, config: Dict[str, Any] = None, logger: logging.Logger = None):
        """
        初始化工具注册中心
        
        Args:
            config: 配置字典
            logger: 日志器
        """
        super().__init__(config, logger)
        
        self.data_processor = None
        self.file_manager = None
        self.registry_data = {}
        self.indexes = {
            'by_name': {},
            'by_category': {},
            'by_scenario': {},
            'by_domain': {}
        }
    
    def _setup(self):
        """设置组件"""
        from config.settings import settings
        
        # 初始化数据处理器
        self.data_processor = DataProcessor(self.logger)
        
        # 初始化文件管理器
        data_path = settings.get_data_path('tools')
        self.file_manager = FileManager(data_path, self.logger)
        
        # 加载已有的注册表
        self._load_registry()
    
    def process(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        注册工具
        
        Args:
            input_data: 包含tools的字典
            **kwargs: 其他参数
            
        Returns:
            注册结果
        """
        try:
            tools = input_data.get('tools', [])
            
            if not tools:
                self.logger.warning("No tools provided for registration")
                return {'registered_count': 0, 'errors': []}
            
            self.logger.info(f"Registering {len(tools)} tools")
            
            registered_count = 0
            errors = []
            
            for tool in tools:
                try:
                    success = self.register_tool(tool)
                    if success:
                        registered_count += 1
                    else:
                        errors.append(f"Failed to register tool: {tool.get('name', 'Unknown')}")
                except Exception as e:
                    errors.append(f"Error registering tool {tool.get('name', 'Unknown')}: {e}")
            
            # 保存注册表
            self._save_registry()
            
            result = {
                'registered_count': registered_count,
                'total_tools': len(self.registry_data),
                'errors': errors
            }
            
            self.logger.info(f"Registered {registered_count} tools, total: {len(self.registry_data)}")
            return result
            
        except Exception as e:
            self.logger.error(f"Tool registration failed: {e}")
            raise RegistryError(f"Failed to register tools: {e}")
    
    def register_tool(self, tool: Dict[str, Any]) -> bool:
        """
        注册单个工具
        
        Args:
            tool: 工具数据
            
        Returns:
            是否注册成功
        """
        try:
            tool_id = tool.get('id')
            tool_name = tool.get('name')
            
            if not tool_id or not tool_name:
                self.logger.error(f"Tool missing required fields: id or name")
                return False
            
            # 检查是否已存在
            if tool_id in self.registry_data:
                self.logger.warning(f"Tool {tool_name} already registered, updating...")
            
            # 验证工具数据
            if not self.data_processor.validate_tool(tool):
                self.logger.error(f"Tool validation failed: {tool_name}")
                return False
            
            # 添加注册信息
            tool['registered_at'] = datetime.now().isoformat()
            tool['registry_version'] = self.metadata.get('version', '1.0.0')
            
            # 注册到主表
            self.registry_data[tool_id] = tool
            
            # 更新索引
            self._update_indexes(tool)
            
            self.logger.debug(f"Registered tool: {tool_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register tool: {e}")
            return False
    
    def unregister_tool(self, tool_id: str) -> bool:
        """
        注销工具
        
        Args:
            tool_id: 工具ID
            
        Returns:
            是否注销成功
        """
        try:
            if tool_id not in self.registry_data:
                self.logger.warning(f"Tool {tool_id} not found in registry")
                return False
            
            tool = self.registry_data[tool_id]
            
            # 从主表删除
            del self.registry_data[tool_id]
            
            # 更新索引
            self._remove_from_indexes(tool)
            
            # 保存注册表
            self._save_registry()
            
            self.logger.info(f"Unregistered tool: {tool.get('name', tool_id)}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unregister tool {tool_id}: {e}")
            return False
    
    def get_tool(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """
        获取工具信息
        
        Args:
            tool_id: 工具ID
            
        Returns:
            工具信息，如果不存在返回None
        """
        return self.registry_data.get(tool_id)
    
    def get_tool_by_name(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        根据名称获取工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            工具信息，如果不存在返回None
        """
        tool_id = self.indexes['by_name'].get(tool_name)
        if tool_id:
            return self.registry_data.get(tool_id)
        return None
    
    def search_tools(self, **criteria) -> List[Dict[str, Any]]:
        """
        搜索工具
        
        Args:
            **criteria: 搜索条件
            
        Returns:
            匹配的工具列表
        """
        try:
            results = []
            
            # 根据不同条件搜索
            if 'category' in criteria:
                category = criteria['category']
                tool_ids = self.indexes['by_category'].get(category, set())
                results.extend([self.registry_data[tid] for tid in tool_ids if tid in self.registry_data])
            
            elif 'scenario_id' in criteria:
                scenario_id = criteria['scenario_id']
                tool_ids = self.indexes['by_scenario'].get(scenario_id, set())
                results.extend([self.registry_data[tid] for tid in tool_ids if tid in self.registry_data])
            
            elif 'domain' in criteria:
                domain = criteria['domain']
                tool_ids = self.indexes['by_domain'].get(domain, set())
                results.extend([self.registry_data[tid] for tid in tool_ids if tid in self.registry_data])
            
            elif 'keyword' in criteria:
                keyword = criteria['keyword'].lower()
                for tool in self.registry_data.values():
                    tool_text = f"{tool.get('name', '')} {tool.get('description', '')}".lower()
                    if keyword in tool_text:
                        results.append(tool)
            
            else:
                # 返回所有工具
                results = list(self.registry_data.values())
            
            # 应用额外过滤条件
            if 'name_pattern' in criteria:
                pattern = criteria['name_pattern'].lower()
                results = [t for t in results if pattern in t.get('name', '').lower()]
            
            if 'has_parameters' in criteria:
                has_params = criteria['has_parameters']
                if has_params:
                    results = [t for t in results if t.get('parameters')]
                else:
                    results = [t for t in results if not t.get('parameters')]
            
            return results
            
        except Exception as e:
            self.logger.error(f"Tool search failed: {e}")
            return []
    
    def get_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        根据类别获取工具
        
        Args:
            category: 工具类别
            
        Returns:
            工具列表
        """
        return self.search_tools(category=category)
    
    def get_tools_by_scenario(self, scenario_id: str) -> List[Dict[str, Any]]:
        """
        根据场景获取工具
        
        Args:
            scenario_id: 场景ID
            
        Returns:
            工具列表
        """
        return self.search_tools(scenario_id=scenario_id)
    
    def get_compatible_tools(self, tool_id: str, max_count: int = 5) -> List[Dict[str, Any]]:
        """
        获取兼容的工具（同类别或同场景）
        
        Args:
            tool_id: 基准工具ID
            max_count: 最大返回数量
            
        Returns:
            兼容工具列表
        """
        try:
            base_tool = self.get_tool(tool_id)
            if not base_tool:
                return []
            
            compatible_tools = []
            
            # 获取同类别工具
            category_tools = self.get_tools_by_category(base_tool.get('category', ''))
            compatible_tools.extend([t for t in category_tools if t.get('id') != tool_id])
            
            # 获取同场景工具
            scenario_ids = base_tool.get('scenario_ids', [])
            for scenario_id in scenario_ids:
                scenario_tools = self.get_tools_by_scenario(scenario_id)
                compatible_tools.extend([t for t in scenario_tools if t.get('id') != tool_id])
            
            # 去重并限制数量
            seen_ids = set()
            unique_tools = []
            for tool in compatible_tools:
                tool_id = tool.get('id')
                if tool_id not in seen_ids:
                    seen_ids.add(tool_id)
                    unique_tools.append(tool)
                    
                    if len(unique_tools) >= max_count:
                        break
            
            return unique_tools
            
        except Exception as e:
            self.logger.error(f"Failed to get compatible tools: {e}")
            return []
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """
        获取注册表统计信息
        
        Returns:
            统计信息
        """
        try:
            total_tools = len(self.registry_data)
            categories = len(self.indexes['by_category'])
            scenarios = len(self.indexes['by_scenario'])
            domains = len(self.indexes['by_domain'])
            
            # 统计各类别工具数量
            category_stats = {}
            for category, tool_ids in self.indexes['by_category'].items():
                category_stats[category] = len(tool_ids)
            
            # 统计参数最多的工具
            max_params = 0
            most_complex_tool = None
            for tool in self.registry_data.values():
                param_count = len(tool.get('parameters', []))
                if param_count > max_params:
                    max_params = param_count
                    most_complex_tool = tool.get('name', '')
            
            return {
                'total_tools': total_tools,
                'total_categories': categories,
                'total_scenarios': scenarios,
                'total_domains': domains,
                'category_distribution': category_stats,
                'most_complex_tool': {
                    'name': most_complex_tool,
                    'parameter_count': max_params
                },
                'registry_size_mb': self._get_registry_size(),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get registry stats: {e}")
            return {}
    
    def _update_indexes(self, tool: Dict[str, Any]):
        """
        更新索引
        
        Args:
            tool: 工具数据
        """
        tool_id = tool.get('id')
        tool_name = tool.get('name')
        category = tool.get('category', '')
        scenario_ids = tool.get('scenario_ids', [])
        domain = tool.get('metadata', {}).get('domain', '')
        
        # 更新名称索引
        if tool_name:
            self.indexes['by_name'][tool_name] = tool_id
        
        # 更新类别索引
        if category:
            if category not in self.indexes['by_category']:
                self.indexes['by_category'][category] = set()
            self.indexes['by_category'][category].add(tool_id)
        
        # 更新场景索引
        for scenario_id in scenario_ids:
            if scenario_id:
                if scenario_id not in self.indexes['by_scenario']:
                    self.indexes['by_scenario'][scenario_id] = set()
                self.indexes['by_scenario'][scenario_id].add(tool_id)
        
        # 更新领域索引
        if domain:
            if domain not in self.indexes['by_domain']:
                self.indexes['by_domain'][domain] = set()
            self.indexes['by_domain'][domain].add(tool_id)
    
    def _remove_from_indexes(self, tool: Dict[str, Any]):
        """
        从索引中移除工具
        
        Args:
            tool: 工具数据
        """
        tool_id = tool.get('id')
        tool_name = tool.get('name')
        category = tool.get('category', '')
        scenario_ids = tool.get('scenario_ids', [])
        domain = tool.get('metadata', {}).get('domain', '')
        
        # 从名称索引移除
        if tool_name and tool_name in self.indexes['by_name']:
            del self.indexes['by_name'][tool_name]
        
        # 从类别索引移除
        if category and category in self.indexes['by_category']:
            self.indexes['by_category'][category].discard(tool_id)
            if not self.indexes['by_category'][category]:
                del self.indexes['by_category'][category]
        
        # 从场景索引移除
        for scenario_id in scenario_ids:
            if scenario_id and scenario_id in self.indexes['by_scenario']:
                self.indexes['by_scenario'][scenario_id].discard(tool_id)
                if not self.indexes['by_scenario'][scenario_id]:
                    del self.indexes['by_scenario'][scenario_id]
        
        # 从领域索引移除
        if domain and domain in self.indexes['by_domain']:
            self.indexes['by_domain'][domain].discard(tool_id)
            if not self.indexes['by_domain'][domain]:
                del self.indexes['by_domain'][domain]
    
    def _load_registry(self):
        """加载注册表数据"""
        try:
            registry_file = "tool_registry.json"
            indexes_file = "tool_indexes.json"
            
            # 加载主注册表
            try:
                self.registry_data = self.file_manager.load_json(registry_file)
                self.logger.info(f"Loaded {len(self.registry_data)} tools from registry")
            except:
                self.registry_data = {}
                self.logger.info("Created new tool registry")
            
            # 加载索引
            try:
                indexes_data = self.file_manager.load_json(indexes_file)
                # 转换set数据
                for index_name, index_data in indexes_data.items():
                    if index_name in ['by_category', 'by_scenario', 'by_domain']:
                        self.indexes[index_name] = {k: set(v) for k, v in index_data.items()}
                    else:
                        self.indexes[index_name] = index_data
                self.logger.info("Loaded tool indexes")
            except:
                self._rebuild_indexes()
                self.logger.info("Rebuilt tool indexes")
                
        except Exception as e:
            self.logger.error(f"Failed to load registry: {e}")
    
    def _save_registry(self):
        """保存注册表数据"""
        try:
            registry_file = "tool_registry.json"
            indexes_file = "tool_indexes.json"
            
            # 保存主注册表
            self.file_manager.save_json(self.registry_data, registry_file)
            
            # 保存索引（转换set为list）
            indexes_to_save = {}
            for index_name, index_data in self.indexes.items():
                if index_name in ['by_category', 'by_scenario', 'by_domain']:
                    indexes_to_save[index_name] = {k: list(v) for k, v in index_data.items()}
                else:
                    indexes_to_save[index_name] = index_data
            
            self.file_manager.save_json(indexes_to_save, indexes_file)
            
            self.logger.debug("Saved tool registry and indexes")
            
        except Exception as e:
            self.logger.error(f"Failed to save registry: {e}")
    
    def _rebuild_indexes(self):
        """重建索引"""
        try:
            self.indexes = {
                'by_name': {},
                'by_category': {},
                'by_scenario': {},
                'by_domain': {}
            }
            
            for tool in self.registry_data.values():
                self._update_indexes(tool)
            
            self.logger.info("Rebuilt tool indexes")
            
        except Exception as e:
            self.logger.error(f"Failed to rebuild indexes: {e}")
    
    def _get_registry_size(self) -> float:
        """
        获取注册表大小（MB）
        
        Returns:
            大小（MB）
        """
        try:
            import sys
            size_bytes = sys.getsizeof(self.registry_data) + sys.getsizeof(self.indexes)
            return round(size_bytes / (1024 * 1024), 2)
        except:
            return 0.0 