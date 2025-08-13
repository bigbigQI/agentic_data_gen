"""
工具组合生成器
基于场景内工具的相似度构建图，通过随机游走生成工具组合
"""

import random
from typing import Dict, Any, List, Tuple, Set
import logging
from datetime import datetime
from collections import defaultdict

from core.base_module import BaseModule
from core.exceptions import AgentDataGenException
from utils.data_processor import DataProcessor
from .tool_graph import ToolGraph


class ToolCombinationGenerator(BaseModule):
    """工具组合生成器"""
    
    def __init__(self, config: Dict[str, Any] = None, logger: logging.Logger = None):
        """
        初始化工具组合生成器
        
        Args:
            config: 配置字典
            logger: 日志器
        """
        super().__init__(config, logger)
        
        self.data_processor = None
        self.tool_graph = None
        
        # 配置参数
        self.min_tools_per_agent = 3
        self.max_tools_per_agent = 6
        self.target_agent_count = 1000
        
        # 场景分布配置
        self.scenario_sampling_weights = {}  # scenario_id -> weight
        self.max_agents_per_scenario = 50   # 每个场景最多生成的智能体数量
        
    def _setup(self):
        """设置组件"""
        from config.settings import settings
        
        # 初始化数据处理器
        self.data_processor = DataProcessor(self.logger)
        
        # 初始化工具图
        self.tool_graph = ToolGraph(logger=self.logger)
        self.tool_graph.initialize()
        
        # 从配置读取参数
        agent_config = settings.GENERATION_CONFIG.get('agents', {})
        self.target_agent_count = agent_config.get('target_count', 1000)
        
        tools_per_agent = agent_config.get('tools_per_agent', {})
        self.min_tools_per_agent = tools_per_agent.get('min', 3)
        self.max_tools_per_agent = tools_per_agent.get('max', 6)
    
    def process(self, input_data: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
        """
        生成工具组合
        
        Args:
            input_data: 包含工具数据的字典
            **kwargs: 其他参数
            
        Returns:
            工具组合列表
        """
        try:
            tools = input_data.get('tools', [])
            target_count = input_data.get('target_count', self.target_agent_count)
            
            if not tools:
                raise AgentDataGenException("No tools provided")
            
            self.logger.info(f"Generating {target_count} tool combinations from {len(tools)} tools")
            
            # 1. 按场景分组工具
            scenario_groups = self._group_tools_by_scenario(tools)
            self.logger.info(f"Found {len(scenario_groups)} scenario groups")
            
            # 2. 为每个场景构建工具图
            scenario_graphs = self._build_scenario_graphs(scenario_groups)
            
            # 3. 生成工具组合
            combinations = self._generate_combinations_from_scenarios(
                scenario_graphs, target_count
            )
            
            # 4. 去重和验证
            unique_combinations = self._deduplicate_combinations(combinations)
            
            self.logger.info(f"Generated {len(unique_combinations)} unique tool combinations")
            return unique_combinations
            
        except Exception as e:
            self.logger.error(f"Tool combination generation failed: {e}")
            raise AgentDataGenException(f"Failed to generate tool combinations: {e}")
    
    def _group_tools_by_scenario(self, tools: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """按场景分组工具"""
        scenario_groups = defaultdict(list)
        no_scenario_tools = []
        
        for tool in tools:
            scenario_ids = tool.get('scenario_ids', [])
            
            if scenario_ids:
                # 工具可能属于多个场景，选择第一个作为主场景
                primary_scenario = scenario_ids[0]
                scenario_groups[primary_scenario].append(tool)
                
            else:
                no_scenario_tools.append(tool)
        
        # 过滤掉工具数量太少的场景
        filtered_groups = {
            scenario_id: tools_list 
            for scenario_id, tools_list in scenario_groups.items()
            if len(tools_list) >= self.min_tools_per_agent
        }
        
        self.logger.info(f"Scenario grouping: {len(filtered_groups)} valid scenarios")
        for scenario_id, tools_list in filtered_groups.items():
            self.logger.debug(f"  {scenario_id}: {len(tools_list)} tools")
        
        return filtered_groups
    
    def _build_scenario_graphs(self, scenario_groups: Dict[str, List[Dict[str, Any]]]) -> Dict[str, ToolGraph]:
        """为每个场景构建工具图"""
        scenario_graphs = {}
        
        for scenario_id, tools_list in scenario_groups.items():
            try:
                # 创建新的工具图实例
                graph = ToolGraph(logger=self.logger)
                graph.initialize()
                
                # 构建图
                graph.process({'tools': tools_list})
                
                scenario_graphs[scenario_id] = graph
                
                self.logger.debug(f"Built graph for scenario {scenario_id}: "
                                f"{graph.graph.number_of_nodes()} nodes, "
                                f"{graph.graph.number_of_edges()} edges")
                
            except Exception as e:
                self.logger.error(f"Failed to build graph for scenario {scenario_id}: {e}")
                continue
        
        return scenario_graphs
    
    def _generate_combinations_from_scenarios(self, scenario_graphs: Dict[str, ToolGraph], 
                                            target_count: int) -> List[Dict[str, Any]]:
        """从各场景生成工具组合"""
        combinations = []
        
        # # 计算每个场景应该生成的组合数量
        # scenario_allocation = self._allocate_combinations_to_scenarios(
        #     scenario_graphs, target_count
        # )
        
        for scenario_id, graph in scenario_graphs.items():
            target_for_scenario = target_count
                        
            scenario_combinations = self._generate_combinations_for_scenario(
                scenario_id, graph, target_for_scenario
            )
            
            combinations.extend(scenario_combinations)
        
        return combinations
    
    # def _allocate_combinations_to_scenarios(self, scenario_graphs: Dict[str, ToolGraph], 
    #                                       target_count: int) -> Dict[str, int]:
    #     """为各场景分配组合数量"""
    #     if not scenario_graphs:
    #         return {}
        
    #     # 基于场景的工具数量和连通性分配权重
    #     scenario_weights = {}
    #     total_weight = 0
        
    #     for scenario_id, graph in scenario_graphs.items():
    #         node_count = graph.graph.number_of_nodes()
    #         edge_count = graph.graph.number_of_edges()
            
    #         # 权重基于工具数量和连接度
    #         weight = node_count * 0.7 + (edge_count / max(node_count, 1)) * 0.3
    #         scenario_weights[scenario_id] = weight
    #         total_weight += weight
        
    #     # 分配组合数量
    #     allocation = {}
    #     allocated_total = 0
        
    #     # 按权重分配，但确保每个场景至少有一定数量
    #     min_per_scenario = max(1, target_count // (len(scenario_graphs) * 3))
        
    #     for scenario_id, weight in scenario_weights.items():
    #         if total_weight > 0:
    #             proportion = weight / total_weight
    #             allocated = max(min_per_scenario, int(target_count * proportion))
    #         else:
    #             allocated = target_count // len(scenario_graphs)
            
    #         # 限制每个场景的最大数量
    #         allocated = min(allocated, self.max_agents_per_scenario)
    #         allocation[scenario_id] = allocated
    #         allocated_total += allocated
        
    #     # 如果分配总数不足，补充到最大的场景
    #     if allocated_total < target_count:
    #         remaining = target_count - allocated_total
    #         largest_scenario = max(scenario_weights.keys(), key=lambda x: scenario_weights[x])
    #         allocation[largest_scenario] += remaining
        
    #     return allocation
    
    def _generate_combinations_for_scenario(self, scenario_id: str, graph: ToolGraph, 
                                          target_count: int) -> List[Dict[str, Any]]:
        """为单个场景生成工具组合"""
        combinations = []
        available_tools = list(graph.graph.nodes())
        
        if len(available_tools) < self.min_tools_per_agent:
            self.logger.warning(f"Scenario {scenario_id} has too few tools: {len(available_tools)}")
            return combinations
        
        # 使用多种策略生成组合
        # strategies = [
        #     ('random_walk', 0.6),
        #     ('cluster_based', 0.3),
        #     ('random_sampling', 0.1)
        # ]
        
        # for strategy, proportion in strategies:
        #     strategy_count = int(target_count * proportion)
            
        #     if strategy == 'random_walk':
        combinations = self._generate_random_walk_combinations(
            scenario_id, graph, target_count
        )
            # elif strategy == 'cluster_based':
            #     strategy_combinations = self._generate_cluster_based_combinations(
            #         scenario_id, graph, strategy_count
            #     )
            # else:  # random_sampling
            #     strategy_combinations = self._generate_random_combinations(
            #         scenario_id, available_tools, strategy_count
            #     )
        
        return combinations[:target_count]
    
    def _generate_random_walk_combinations(self, scenario_id: str, graph: ToolGraph, 
                                         count: int) -> List[Dict[str, Any]]:
        """使用随机游走生成组合"""
        combinations = []
        available_tools = list(graph.graph.nodes())
        
        for i in range(count):
            # 随机选择起始工具
            start_tool = random.choice(available_tools)
            
            # 确定组合大小
            combo_size = random.randint(self.min_tools_per_agent, self.max_tools_per_agent)
            
            # 执行随机游走
            selected_tools = graph.random_walk_selection(start_tool, combo_size - 1)
            
            # 确保包含起始工具
            if start_tool not in selected_tools:
                selected_tools.insert(0, start_tool)
            
            # 限制大小
            selected_tools = selected_tools[:combo_size]
            
            # 如果工具数量不足，随机补充
            while len(selected_tools) < self.min_tools_per_agent:
                remaining_tools = [t for t in available_tools if t not in selected_tools]
                if not remaining_tools:
                    break
                selected_tools.append(random.choice(remaining_tools))
            
            if len(selected_tools) >= self.min_tools_per_agent:
                combination = self._create_combination_record(
                    scenario_id, selected_tools, 'random_walk', start_tool
                )
                combinations.append(combination)
        
        return combinations
    
    # def _generate_cluster_based_combinations(self, scenario_id: str, graph: ToolGraph, 
    #                                        count: int) -> List[Dict[str, Any]]:
    #     """基于工具簇生成组合"""
    #     combinations = []
    #     available_tools = list(graph.graph.nodes())
        
    #     for i in range(count):
    #         # 随机选择起始工具
    #         start_tool = random.choice(available_tools)
            
    #         # 获取工具簇
    #         cluster_size = random.randint(self.min_tools_per_agent, self.max_tools_per_agent)
    #         cluster = graph.get_tool_cluster(start_tool, cluster_size)
            
    #         if len(cluster) >= self.min_tools_per_agent:
    #             combination = self._create_combination_record(
    #                 scenario_id, cluster, 'cluster_based', start_tool
    #             )
    #             combinations.append(combination)
        
    #     return combinations
    
    # def _generate_random_combinations(self, scenario_id: str, available_tools: List[str], 
    #                                 count: int) -> List[Dict[str, Any]]:
    #     """生成随机工具组合"""
    #     combinations = []
        
    #     for i in range(count):
    #         combo_size = random.randint(self.min_tools_per_agent, self.max_tools_per_agent)
            
    #         if len(available_tools) >= combo_size:
    #             selected_tools = random.sample(available_tools, combo_size)
                
    #             combination = self._create_combination_record(
    #                 scenario_id, selected_tools, 'random_sampling', selected_tools[0]
    #             )
    #             combinations.append(combination)
        
    #     return combinations
    
    def _create_combination_record(self, scenario_id: str, tool_ids: List[str], 
                                 method: str, start_tool: str) -> Dict[str, Any]:
        """创建组合记录"""
        combination_id = self.data_processor.generate_id('combination', {
            'scenario': scenario_id,
            'tools': sorted(tool_ids),
            'timestamp': datetime.now().isoformat()
        })
        
        return {
            'id': combination_id,
            'scenario_id': scenario_id,
            'tool_ids': tool_ids,
            'generation_method': method,
            'start_tool': start_tool,
            'tool_count': len(tool_ids),
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'scenario_id': scenario_id,
                'generation_strategy': method
            }
        }
    
    def _deduplicate_combinations(self, combinations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去除重复的工具组合"""
        seen_signatures = set()
        unique_combinations = []
        
        for combo in combinations:
            # 创建组合签名（忽略顺序）
            tool_signature = tuple(sorted(combo['tool_ids']))
            
            if tool_signature not in seen_signatures:
                seen_signatures.add(tool_signature)
                unique_combinations.append(combo)
        
        return unique_combinations
    
    def get_combination_stats(self, combinations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取组合统计信息"""
        if not combinations:
            return {}
        
        from collections import Counter
        
        # 基础统计
        total_combinations = len(combinations)
        tool_counts = [len(combo['tool_ids']) for combo in combinations]
        
        # 方法分布
        methods = [combo.get('generation_method', '') for combo in combinations]
        method_dist = Counter(methods)
        
        # 场景分布
        scenarios = [combo.get('scenario_id', '') for combo in combinations]
        scenario_dist = Counter(scenarios)
        
        # 工具使用统计
        all_tools = []
        for combo in combinations:
            all_tools.extend(combo['tool_ids'])
        tool_usage = Counter(all_tools)
        
        return {
            'total_combinations': total_combinations,
            'tool_count_distribution': {
                'min': min(tool_counts),
                'max': max(tool_counts),
                'avg': sum(tool_counts) / len(tool_counts),
                'distribution': dict(Counter(tool_counts))
            },
            'generation_method_distribution': dict(method_dist),
            'scenario_distribution': dict(scenario_dist.most_common(10)),
            'tool_usage_stats': {
                'unique_tools_used': len(tool_usage),
                'most_used_tools': dict(tool_usage.most_common(10)),
                'avg_usage_per_tool': sum(tool_usage.values()) / len(tool_usage)
            }
        }
