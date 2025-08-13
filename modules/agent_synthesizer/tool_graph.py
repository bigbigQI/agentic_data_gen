"""
工具关系图构建和随机游走模块
用于构建工具之间的关系图，并通过随机游走选择相关工具
"""

import random
from typing import Dict, Any, List, Optional, Tuple, Set
import logging
from datetime import datetime

import networkx as nx
import numpy as np
from core.base_module import BaseModule
from core.exceptions import AgentDataGenException
from utils.file_manager import FileManager
from utils.data_processor import DataProcessor


class ToolGraph(BaseModule):
    """工具关系图构建器"""
    
    def __init__(self, config: Dict[str, Any] = None, logger: logging.Logger = None):
        """
        初始化工具关系图构建器
        
        Args:
            config: 配置字典
            logger: 日志器
        """
        super().__init__(config, logger)
        
        self.graph = None
        self.tools_data = {}  # tool_id -> tool_data映射
        self.file_manager = None
        self.data_processor = None
        
        # 相似度阈值配置
        self.similarity_threshold = 0.7
        self.min_similarity_threshold = 0.5
        self.max_edges_per_node = 10
        
        # 随机游走参数
        self.walk_length = 6  # 最大游走长度
        self.restart_probability = 0.15  # 重启概率
        
    def _setup(self):
        """设置组件"""
        from config.settings import settings
        
        # 初始化文件管理器
        data_path = settings.get_data_path('tools')
        self.file_manager = FileManager(data_path, self.logger)
        
        # 初始化数据处理器
        self.data_processor = DataProcessor(self.logger)
        
        # 初始化图
        self.graph = nx.Graph()
    
    def process(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        构建工具关系图
        
        Args:
            input_data: 包含工具数据的字典
            **kwargs: 其他参数
            
        Returns:
            包含图统计信息的字典
        """
        try:
            tools = input_data.get('tools', [])
            
            if not tools:
                raise AgentDataGenException("No tools data provided")
            
            # 构建图
            self.build_graph(tools)
            
            # 生成统计信息
            stats = self._generate_graph_stats()
            
            # 保存图数据
            self._save_graph_data()
            
            self.logger.info(f"Successfully built tool graph with {len(tools)} tools")
            return stats
            
        except Exception as e:
            self.logger.error(f"Tool graph building failed: {e}")
            raise AgentDataGenException(f"Failed to build tool graph: {e}")
    
    def build_graph(self, tools: List[Dict[str, Any]]) -> None:
        """
        构建工具关系图
        
        Args:
            tools: 工具列表
        """
        try:
            self.logger.info(f"Building tool graph for {len(tools)} tools")
            
            # 清空现有图
            self.graph.clear()
            self.tools_data.clear()
            
            # 添加节点
            for tool in tools:
                tool_id = tool.get('id')
                if tool_id:
                    self.graph.add_node(tool_id, **tool)
                    self.tools_data[tool_id] = tool
            
            # 构建边（基于相似度）
            self._build_edges_by_similarity(tools)
            
            
            self.logger.info(f"Graph built with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")
            
        except Exception as e:
            self.logger.error(f"Failed to build graph: {e}")
            raise AgentDataGenException(f"Graph building failed: {e}")
    
    def _build_edges_by_similarity(self, tools: List[Dict[str, Any]]):
        """基于embedding相似度构建边"""
        tools_with_embeddings = [
            tool for tool in tools 
            if tool.get('metadata').get('embedding')
        ]
        
        self.logger.info(f"Building similarity edges for {len(tools_with_embeddings)} tools with embeddings")
        
        # 计算所有工具对之间的相似度
        for i, tool1 in enumerate(tools_with_embeddings):
            tool1_id = tool1.get('id')
            tool1_embedding = tool1['metadata']['embedding']
            
            similarities = []
            for j, tool2 in enumerate(tools_with_embeddings):
                if i >= j:  # 避免重复计算
                    continue
                    
                tool2_id = tool2.get('id')
                tool2_embedding = tool2['metadata']['embedding']
                
                similarity = self._calculate_cosine_similarity(tool1_embedding, tool2_embedding)
                
                if similarity >= self.min_similarity_threshold:
                    similarities.append((tool2_id, similarity))
            
            # 为每个工具保留最相似的几个工具作为邻居
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            for tool2_id, similarity in similarities[:self.max_edges_per_node]:
                if similarity >= self.similarity_threshold:
                    self.graph.add_edge(tool1_id, tool2_id, weight=similarity, edge_type='similarity')
    
    def _build_edges_by_category_and_domain(self, tools: List[Dict[str, Any]]):
        """基于类别和领域构建边"""
        category_groups = {}
        domain_groups = {}
        
        # 按类别和领域分组
        for tool in tools:
            tool_id = tool.get('id')
            category = tool.get('category', '')
            domain = tool.get('metadata', {}).get('domain', '')
            
            if category:
                if category not in category_groups:
                    category_groups[category] = []
                category_groups[category].append(tool_id)
            
            if domain:
                if domain not in domain_groups:
                    domain_groups[domain] = []
                domain_groups[domain].append(tool_id)
        
        # 在同类别的工具间添加边
        for category, tool_ids in category_groups.items():
            if len(tool_ids) > 1:
                self._add_group_edges(tool_ids, 'category', weight=0.6)
        
        # 在同领域的工具间添加边
        for domain, tool_ids in domain_groups.items():
            if len(tool_ids) > 1:
                self._add_group_edges(tool_ids, 'domain', weight=0.5)
    
    def _add_group_edges(self, tool_ids: List[str], edge_type: str, weight: float):
        """为工具组添加边"""
        # 避免完全连接，只连接部分工具
        for i, tool1_id in enumerate(tool_ids):
            # 随机选择几个工具连接
            connection_count = min(3, len(tool_ids) - 1)
            other_tools = [tid for tid in tool_ids if tid != tool1_id]
            connected_tools = random.sample(other_tools, min(connection_count, len(other_tools)))
            
            for tool2_id in connected_tools:
                if not self.graph.has_edge(tool1_id, tool2_id):
                    self.graph.add_edge(tool1_id, tool2_id, weight=weight, edge_type=edge_type)
    
    def _calculate_cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """计算余弦相似度"""
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot_product / (norm1 * norm2)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate cosine similarity: {e}")
            return 0.0
    
    def random_walk_selection(self, start_tool: str, count: int, restart_prob: float = None) -> List[str]:
        """
        使用随机游走选择相关工具
        
        Args:
            start_tool: 起始工具ID
            count: 需要选择的工具数量
            restart_prob: 重启概率
            
        Returns:
            选中的工具ID列表
        """
        if start_tool not in self.graph:
            self.logger.warning(f"Start tool {start_tool} not found in graph")
            return []
        
        restart_prob = restart_prob or self.restart_probability
        selected_tools = set()
        current_tool = start_tool
        
        # 随机游走
        for _ in range(self.walk_length * count):
            if len(selected_tools) >= count:
                break
            
            # 添加当前工具
            selected_tools.add(current_tool)
            
            # 决定是否重启
            if random.random() < restart_prob:
                current_tool = start_tool
                continue
            
            # 获取邻居节点
            neighbors = list(self.graph.neighbors(current_tool))
            if not neighbors:
                current_tool = start_tool
                continue
            
            # 根据边权重选择下一个节点
            next_tool = self._weighted_random_choice(current_tool, neighbors)
            current_tool = next_tool
        
        # 移除起始工具，因为它不算在选择结果中
        selected_tools.discard(start_tool)
        
        # 如果选择的工具不够，补充最相似的工具
        if len(selected_tools) < count:
            additional_tools = self.get_related_tools(start_tool, count - len(selected_tools))
            selected_tools.update(additional_tools)
        
        return list(selected_tools)[:count]
    
    def _weighted_random_choice(self, current_tool: str, neighbors: List[str]) -> str:
        """根据边权重随机选择邻居"""
        try:
            weights = []
            for neighbor in neighbors:
                edge_data = self.graph.get_edge_data(current_tool, neighbor)
                weight = edge_data.get('weight', 0.5) if edge_data else 0.5
                weights.append(weight)
            
            # 归一化权重
            total_weight = sum(weights)
            if total_weight == 0:
                return random.choice(neighbors)
            
            weights = [w / total_weight for w in weights]
            
            # 根据权重随机选择
            return np.random.choice(neighbors, p=weights)
            
        except Exception as e:
            self.logger.error(f"Failed to make weighted random choice: {e}")
            return random.choice(neighbors)
    
    def get_related_tools(self, tool_id: str, max_count: int) -> List[str]:
        """
        获取与指定工具相关的工具
        
        Args:
            tool_id: 工具ID
            max_count: 最大数量
            
        Returns:
            相关工具ID列表
        """
        if tool_id not in self.graph:
            return []
        
        # 获取直接邻居
        neighbors = list(self.graph.neighbors(tool_id))
        
        # 按边权重排序
        neighbor_weights = []
        for neighbor in neighbors:
            edge_data = self.graph.get_edge_data(tool_id, neighbor)
            weight = edge_data.get('weight', 0.5) if edge_data else 0.5
            neighbor_weights.append((neighbor, weight))
        
        neighbor_weights.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前max_count个邻居
        return [neighbor for neighbor, _ in neighbor_weights[:max_count]]
    
    def get_tool_cluster(self, tool_id: str, max_size: int = 6) -> List[str]:
        """
        获取包含指定工具的工具簇
        
        Args:
            tool_id: 工具ID
            max_size: 簇的最大大小
            
        Returns:
            工具簇中的工具ID列表
        """
        if tool_id not in self.graph:
            return [tool_id] if tool_id in self.tools_data else []
        
        # 使用BFS构建工具簇
        visited = set()
        queue = [tool_id]
        cluster = []
        
        while queue and len(cluster) < max_size:
            current = queue.pop(0)
            if current in visited:
                continue
                
            visited.add(current)
            cluster.append(current)
            
            # 添加邻居到队列
            neighbors = list(self.graph.neighbors(current))
            for neighbor in neighbors:
                if neighbor not in visited and len(cluster) + len(queue) < max_size:
                    queue.append(neighbor)
        
        return cluster
    
    def _load_tools_data(self, file_path: str) -> List[Dict[str, Any]]:
        """加载工具数据"""
        try:
            return self.file_manager.load_json(file_path)
        except Exception as e:
            self.logger.error(f"Failed to load tools data: {e}")
            return []
    
    def _generate_graph_stats(self) -> Dict[str, Any]:
        """生成图统计信息"""
        try:
            stats = {
                'total_nodes': self.graph.number_of_nodes(),
                'total_edges': self.graph.number_of_edges(),
                'average_degree': sum(dict(self.graph.degree()).values()) / self.graph.number_of_nodes() if self.graph.number_of_nodes() > 0 else 0,
                'connected_components': nx.number_connected_components(self.graph),
                'largest_component_size': len(max(nx.connected_components(self.graph), key=len)) if self.graph.number_of_nodes() > 0 else 0,
                'edge_types': self._count_edge_types(),
                'generated_at': datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to generate graph stats: {e}")
            return {}
    
    def _count_edge_types(self) -> Dict[str, int]:
        """统计边类型"""
        edge_types = {}
        for _, _, data in self.graph.edges(data=True):
            edge_type = data.get('edge_type', 'unknown')
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
        return edge_types
    
    def _save_graph_data(self):
        """保存图数据"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 保存图的边列表格式
            edges_data = []
            for u, v, data in self.graph.edges(data=True):
                edges_data.append({
                    'source': u,
                    'target': v,
                    'weight': data.get('weight', 0.5),
                    'edge_type': data.get('edge_type', 'unknown')
                })
            
            graph_data = {
                'nodes': list(self.graph.nodes()),
                'edges': edges_data,
                'stats': self._generate_graph_stats()
            }
            
            filename = f"tool_graph_{timestamp}.json"
            self.file_manager.save_json(graph_data, filename)
            
            self.logger.info(f"Saved tool graph to {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to save graph data: {e}")
    
    def load_graph_from_file(self, file_path: str) -> bool:
        """
        从文件加载图数据
        
        Args:
            file_path: 图数据文件路径
            
        Returns:
            是否成功加载
        """
        try:
            graph_data = self.file_manager.load_json(file_path)
            
            # 重建图
            self.graph.clear()
            
            # 添加节点
            for node_id in graph_data.get('nodes', []):
                if node_id in self.tools_data:
                    self.graph.add_node(node_id, **self.tools_data[node_id])
                else:
                    self.graph.add_node(node_id)
            
            # 添加边
            for edge in graph_data.get('edges', []):
                self.graph.add_edge(
                    edge['source'], 
                    edge['target'],
                    weight=edge.get('weight', 0.5),
                    edge_type=edge.get('edge_type', 'unknown')
                )
            
            self.logger.info(f"Successfully loaded graph from {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load graph from file: {e}")
            return False