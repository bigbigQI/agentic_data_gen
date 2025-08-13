"""
工具设计器
基于场景设计和生成相关工具
"""

from typing import Dict, Any, List
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.base_module import BaseModule
from core.models import Tool, ToolParameter
from core.exceptions import ToolDesignError
from config.prompts.tool_prompts import ToolPrompts
from utils.llm_client import LLMClient
from utils.data_processor import DataProcessor
from utils.file_manager import FileManager


class ToolDesigner(BaseModule):
    """工具设计器"""
    
    def __init__(self, config: Dict[str, Any] = None, logger: logging.Logger = None):
        """
        初始化工具设计器
        
        Args:
            config: 配置字典
            logger: 日志器
        """
        super().__init__(config, logger)
        
        self.llm_client = None
        self.data_processor = None
        self.file_manager = None
        self.prompts = ToolPrompts()
        self.max_workers = 64
    
    def _setup(self):
        """设置组件"""
        from config.settings import settings
        
        # 初始化LLM客户端
        llm_config = settings.get_llm_config()
        llm_config['provider'] = settings.DEFAULT_LLM_PROVIDER
        self.llm_client = LLMClient(llm_config, self.logger)
        
        # 初始化数据处理器
        self.data_processor = DataProcessor(self.logger)
        
        # 初始化文件管理器
        data_path = settings.get_data_path('tools')
        self.file_manager = FileManager(data_path, self.logger)
    
    def process(self, input_data: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
        """
        基于场景生成工具
        
        Args:
            input_data: scenarios
            **kwargs: 其他参数
            
        Returns:
            生成的工具列表
        """
        try:
            scenarios = input_data.get('scenarios', [])
            
            if not scenarios:
                raise ToolDesignError("No scenarios provided")
            tools_per_scenario = self.config.get('tools_per_scenario', 5)
            
            # 并行处理所有场景
            all_tools = []
            total = len(scenarios)
            finished = 0

            def print_progress(finished, total):
                percent = finished / total * 100
                bar_len = 30
                filled_len = int(bar_len * finished // total)
                bar = '█' * filled_len + '-' * (bar_len - filled_len)
                print(f"\r[进度] |{bar}| {finished}/{total} 场景 ({percent:.1f}%)", end='', flush=True)

            print_progress(finished, total)

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有任务
                future_to_scenario = {
                    executor.submit(self._generate_scenario_tools, scenario, tools_per_scenario): scenario 
                    for scenario in scenarios
                }
                
                # 收集结果
                for idx, future in enumerate(as_completed(future_to_scenario), 1):
                    scenario = future_to_scenario[future]
                    try:
                        scenario_tools = future.result()
                        all_tools.extend(scenario_tools)
                        self.logger.debug(f"Completed scenario: {scenario.get('name', 'Unknown')}")
                    except Exception as e:
                        self.logger.error(f"Failed to process scenario {scenario.get('name', 'Unknown')}: {e}")
                        continue
                    finished += 1
                    print_progress(finished, total)
            
            # 保存生成的工具
            self._save_tools(all_tools)
            
            self.logger.info(f"Successfully generated {len(all_tools)} tools from {len(scenarios)} scenarios")
            return all_tools
            
        except Exception as e:
            self.logger.error(f"Tool generation failed: {e}")
            raise ToolDesignError(f"Failed to generate tools: {e}")
    
    def _generate_scenario_tools(self, scenario: Dict[str, Any], count: int) -> List[Dict[str, Any]]:
        """
        为特定场景生成工具
        
        Args:
            scenario: 场景数据
            count: 生成数量
            
        Returns:
            工具列表
        """
        try:
            tools = []
            batch_size = self.config.get('batch_size', 3)
            # 基于场景的用例生成工具
            while len(tools) < count:
                batch_count = min(batch_size, count - len(tools))
                batch_tools = self._generate_tool_batch(scenario, batch_count)
                tools.extend(batch_tools)
            
            return tools
            
        except Exception as e:
            self.logger.error(f"Failed to generate tools for scenario {scenario.get('name', 'Unknown')}: {e}")
            return []
    
    def _generate_tool_batch(self, scenario: Dict[str, Any], count: int) -> List[Dict[str, Any]]:
        """
        生成一批工具
        
        Args:
            scenario: 场景数据
            count: 生成数量
            
        Returns: 
            工具列表
        """
        try:
            prompt = self._build_tool_generation_prompt(scenario, count)
            response = self.llm_client.generate_completion(prompt)
            tools_data = self.llm_client.parse_json_response(response)
            
            # 处理和标准化工具数据
            tools = []
            for tool_data in tools_data:
                if self._validate_tool_data(tool_data):
                    processed_tool = self._process_tool_data(tool_data, scenario)
                    tools.append(processed_tool)
            
            self.logger.debug(f"Generated {len(tools)} tools for scenario: {scenario.get('name', 'Unknown')}")
            return tools
            
        except Exception as e:
            self.logger.error(f"Failed to generate tool batch: {e}")
            return []
    
    def _build_tool_generation_prompt(self, scenario: Dict[str, Any], count: int) -> str:
        """
        构建工具生成提示词
        
        Args:
            scenario: 场景数据
            count: 生成数量
            
        Returns:
            提示词字符串
        """
        return self.prompts.TOOL_GENERATION.format(
            scenario_name=scenario.get('name', ''),
            scenario_description=scenario.get('description', ''),
            scenario_domain=scenario.get('domain', ''),
            scenario_context=scenario.get('context', ''),
            count=count
        )
    
    def _validate_tool_data(self, tool_data: Dict[str, Any]) -> bool:
        """
        验证工具数据
        
        Args:
            tool_data: 工具数据
            
        Returns:
            是否有效
        """
        return self.data_processor.validate_tool(tool_data)
    
    def _process_tool_data(self, tool_data: Dict[str, Any], scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理和标准化工具数据
        
        Args:
            tool_data: 原始工具数据
            scenario: 相关场景
            
        Returns:
            处理后的工具数据
        """
        # 生成唯一ID
        tool_id = self.data_processor.generate_id('tool', tool_data)
        
        # 清理文本内容 
        name = tool_data.get('name', '')
        description = tool_data.get('description', '')
        
        # 处理参数
        parameters = []
        for param_data in tool_data.get('parameters', []):
            parameter = {
                'name': param_data.get('name', ''),
                'type': param_data.get('type', 'string'),
                'description': param_data.get('description', ''),
                'required': param_data.get('required', True),
                'default': param_data.get('default'),
                'enum': param_data.get('enum')
            }
            parameters.append(parameter)
        
        processed_tool = {
            'id': tool_id,
            'name': name,
            'description': description,
            'scenario_ids': [scenario.get('id', '')],
            'parameters': parameters,
            'return_type': tool_data.get('return_type', 'object'),
            'examples': tool_data.get('examples', []),
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'scenario_name': scenario.get('name', ''),
                'domain': scenario.get('domain', ''),
            }
        }
        
        return processed_tool
    
    
    def _save_tools(self, tools: List[Dict[str, Any]]):
        """
        保存生成的工具
        
        Args:
            tools: 工具列表
        """
        try:
            # 保存为JSON文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tools_batch_{timestamp}.json"
            
            self.file_manager.save_json(tools, filename)

            self.logger.info(f"Saved {len(tools)} tools to {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to save tools: {e}")
    
    def refine_tool(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """
        优化单个工具
        
        Args:
            tool: 原始工具
            
        Returns:
            优化后的工具
        """
        try:
            prompt = self.prompts.TOOL_REFINEMENT.format(tool_data=tool)
            
            response = self.llm_client.generate_completion(prompt)
            refined_data = self.llm_client.parse_json_response(response)
            
            return refined_data
            
        except Exception as e:
            self.logger.error(f"Failed to refine tool: {e}")
            return tool
    
    def evaluate_tool_quality(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估工具质量
        
        Args:
            tool: 工具数据
            
        Returns:
            评估结果
        """
        try:
            prompt = self.prompts.TOOL_VALIDATION.format(tool_data=tool)
            
            response = self.llm_client.generate_completion(prompt)
            evaluation = self.llm_client.parse_json_response(response)
            
            return evaluation
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate tool quality: {e}")
            return {'overall_score': 3.0, 'suggestions': []}

    def batch_refine_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量优化工具（多线程版本）
        
        Args:
            tools: 工具列表
            
        Returns:
            优化后的工具列表
        """
        if not tools:
            return []
        
        refined_tools = []
        total = len(tools)
        finished = 0
        
        def print_progress(finished, total):
            percent = finished / total * 100
            bar_len = 30
            filled_len = int(bar_len * finished // total)
            bar = '█' * filled_len + '-' * (bar_len - filled_len)
            print(f"\r[优化进度] |{bar}| {finished}/{total} 工具 ({percent:.1f}%)", end='', flush=True)
        
        print_progress(finished, total)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_tool = {
                executor.submit(self.refine_tool, tool): tool 
                for tool in tools
            }
            
            # 收集结果
            for future in as_completed(future_to_tool):
                tool = future_to_tool[future]
                try:
                    refined_tool = future.result()
                    refined_tools.append(refined_tool)
                except Exception as e:
                    self.logger.error(f"Failed to refine tool {tool.get('name', 'unknown')}: {e}")
                    # 如果优化失败，保留原工具
                    refined_tools.append(tool)
                finally:
                    finished += 1
                    print_progress(finished, total)
        
        print()  # 换行
        self.logger.info(f"Successfully refined {len(refined_tools)} tools")
        return refined_tools
    
    def batch_evaluate_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量评估工具质量
        
        Args:
            tools: 工具列表
            
        Returns:
            评估结果列表
        """
        if not tools:
            return []
        
        evaluations = []
        total = len(tools)
        finished = 0
        
        def print_progress(finished, total):
            percent = finished / total * 100
            bar_len = 30
            filled_len = int(bar_len * finished // total)
            bar = '█' * filled_len + '-' * (bar_len - filled_len)
            print(f"\r[评估进度] |{bar}| {finished}/{total} 工具 ({percent:.1f}%)", end='', flush=True)
        
        print_progress(finished, total)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_tool = {
                executor.submit(self.evaluate_tool_quality, tool): tool 
                for tool in tools
            }
            
            # 收集结果
            for future in as_completed(future_to_tool):
                tool = future_to_tool[future]
                try:
                    evaluation = future.result()
                    evaluation['id'] = tool.get('id', 'unknown')
                    evaluation['name'] = tool.get('name', 'unknown')
                    evaluations.append(evaluation)
                except Exception as e:
                    self.logger.error(f"Failed to evaluate tool {tool.get('name', 'unknown')}: {e}")
                    # 如果评估失败，添加默认评估
                    evaluations.append({
                        'id': tool.get('id', 'unknown'),
                        'name': tool.get('name', 'unknown'),
                        'overall_score': 3.0,
                        'suggestions': ['评估失败，需要手动检查'],
                        'error': str(e)
                    })
                finally:
                    finished += 1
                    print_progress(finished, total)
        
        print()  # 换行
        self.logger.info(f"Successfully evaluated {len(evaluations)} tools")
        return evaluations
    
    def analyze_evaluation_results(self, evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析批量评估结果
        
        Args:
            evaluations: 评估结果列表
            
        Returns:
            分析统计结果
        """
        if not evaluations:
            return {}
        
        total_count = len(evaluations)
        scores = [eval_result.get('overall_score', 0) for eval_result in evaluations if 'overall_score' in eval_result]
        
        if not scores:
            return {'total_count': total_count, 'error': 'No valid scores found'}
        
        avg_score = sum(scores) / len(scores)
        
        # 分数分布
        score_distribution = {
            'excellent': len([s for s in scores if s >= 4.5]),
            'good': len([s for s in scores if 4.0 <= s < 4.5]),
            'average': len([s for s in scores if 3.0 <= s < 4.0]),
            'poor': len([s for s in scores if s < 3.0])
        }
        
        # 统计推荐状态
        recommendations = {}
        for eval_result in evaluations:
            rec = eval_result.get('recommendation', '未知')
            recommendations[rec] = recommendations.get(rec, 0) + 1
        
        return {
            'total_count': total_count,
            'average_score': round(avg_score, 2),
            'min_score': min(scores),
            'max_score': max(scores),
            'score_distribution': score_distribution,
            'recommendations': recommendations,
            'quality_summary': {
                'high_quality_ratio': round((score_distribution['excellent'] + score_distribution['good']) / total_count * 100, 1),
                'needs_improvement_ratio': round(score_distribution['poor'] / total_count * 100, 1)
            }
        }

    def get_generation_stats(self) -> Dict[str, Any]:
        """
        获取工具生成统计信息
        
        Returns:
            统计信息
        """
        return self.get_tool_stats()
    
    def get_tool_stats(self) -> Dict[str, Any]:
        """
        获取工具生成统计信息
        
        Returns:
            统计信息
        """
        try:
            tool_files = self.file_manager.list_files(".", "tools_batch_*.json")
            
            total_tools = 0
            domains = set()
            
            for file_path in tool_files:
                tools = self.file_manager.load_json(file_path)
                total_tools += len(tools)
                
                for tool in tools:
                    domains.add(tool.get('metadata', {}).get('domain', ''))
            
            return {
                'total_tools': total_tools,
                'total_domains': len(domains),
                'batch_files': len(tool_files),
                'domains_list': list(domains)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get tool stats: {e}")
            return {} 