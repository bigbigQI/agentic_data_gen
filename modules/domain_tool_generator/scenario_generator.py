"""
场景生成器
负责基于领域生成多样化的应用场景
"""

import uuid
from typing import Dict, Any, List
from datetime import datetime
import logging

from core.base_module import BaseModule
from core.models import Scenario
from core.exceptions import ScenarioGenerationError
from config.prompts.scenario_prompts import ScenarioPrompts
from utils.llm_client import LLMClient
from utils.data_processor import DataProcessor
from utils.file_manager import FileManager


class ScenarioGenerator(BaseModule):
    """场景生成器"""
    
    def __init__(self, config: Dict[str, Any] = None, logger: logging.Logger = None):
        """
        初始化场景生成器
        
        Args:
            config: 配置字典
            logger: 日志器
        """
        super().__init__(config, logger)
        
        self.llm_client = None
        self.data_processor = None
        self.file_manager = None
        self.prompts = ScenarioPrompts()
    
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
        data_path = settings.get_data_path('scenarios')
        self.file_manager = FileManager(data_path, self.logger)
    
    def process(self, input_data: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
        """
        生成场景
        
        Args:
            input_data: 包含domains和target_count的字典
            **kwargs: 其他参数
            
        Returns:
            生成的场景列表
        """
        try:
            domains = input_data.get('domains', [])
            target_count = input_data.get('target_count', 100)
            
            if not domains:
                raise ScenarioGenerationError("No domains provided")
            
            self.logger.info(f"Generating {target_count} scenarios for {len(domains)} domains")
            
            all_scenarios = []
            scenarios_per_domain = target_count // len(domains)
            
            for domain in domains:
                domain_scenarios = self._generate_domain_scenarios(domain, scenarios_per_domain)
                all_scenarios.extend(domain_scenarios)
            
            # 保存生成的场景
            self._save_scenarios(all_scenarios)
            
            self.logger.info(f"Successfully generated {len(all_scenarios)} scenarios")
            return all_scenarios
            
        except Exception as e:
            self.logger.error(f"Scenario generation failed: {e}")
            raise ScenarioGenerationError(f"Failed to generate scenarios: {e}")
    
    def _generate_domain_scenarios(self, domain: str, count: int) -> List[Dict[str, Any]]:
        """
        为特定领域生成场景
        
        Args:
            domain: 领域名称
            count: 生成数量
            
        Returns:
            场景列表
        """
        scenarios = []
        batch_size = self.config.get('batch_size', 5)
        
        # 循环生成场景直到达到目标数量
        while len(scenarios) < count:
            batch_count = min(batch_size, count - len(scenarios))
            if batch_count <= 0:
                break
            batch_scenarios = self._generate_scenario_batch(domain, batch_count)
            scenarios.extend(batch_scenarios)
        
        return scenarios[:count]
    
    def _generate_scenario_batch(self, domain: str, count: int) -> List[Dict[str, Any]]:
        """
        生成一批场景
        
        Args:
            domain: 领域名称
            count: 生成数量
            
        Returns:
            场景列表
        """
        try:
            prompt = self.prompts.SCENARIO_GENERATION.format(
                domain=domain,
                count=count
            )
            response = self.llm_client.generate_completion(prompt)
            scenarios_data = self.llm_client.parse_json_response(response)
            # 处理和标准化场景数据
            scenarios = []
            for scenario_data in scenarios_data:
                if self._validate_scenario_data(scenario_data):
                    processed_scenario = self._process_scenario_data(scenario_data, domain)
                    scenarios.append(processed_scenario)
            self.logger.debug(f"Generated {len(scenarios)} scenarios for {domain}")
            return scenarios
            
        except Exception as e:
            self.logger.error(f"Failed to generate scenario batch for {domain}: {e}")
            return []
    
    def _validate_scenario_data(self, scenario_data: Dict[str, Any]) -> bool:
        """
        验证场景数据
        
        Args:
            scenario_data: 场景数据
            
        Returns:
            是否有效
        """
        return self.data_processor.validate_scenario(scenario_data)
    
    def _process_scenario_data(self, scenario_data: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """
        处理和标准化场景数据
        
        Args:
            scenario_data: 原始场景数据
            domain: 领域
            
        Returns:
            处理后的场景数据
        """
        # 生成唯一ID
        scenario_id = self.data_processor.generate_id('scenario', scenario_data)
        
        # 清理文本内容
        name = scenario_data.get('name', '')
        description = scenario_data.get('description', '')
        context = scenario_data.get('context', '')
        
        processed_scenario = {
            'id': scenario_id,
            'name': name,
            'description': description,
            'domain': domain,
            'context': context,
            'target_users': scenario_data.get('target_users', []),
            'metadata': {
                'generated_at': datetime.now().isoformat(),
            }
        }
        
        return processed_scenario
    
    def _save_scenarios(self, scenarios: List[Dict[str, Any]]):
        """
        保存生成的场景
        
        Args:
            scenarios: 场景列表
        """
        try:
            # 保存为JSON文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scenarios_batch_{timestamp}.json"
            
            self.file_manager.save_json(scenarios, filename)
            
            # 保存汇总信息
            summary = {
                'total_count': len(scenarios),
                'domains': list(set(s.get('domain', '') for s in scenarios)),
                'generated_at': timestamp
            }
            
            summary_filename = f"scenarios_summary_{timestamp}.json"
            self.file_manager.save_json(summary, summary_filename)
            
            self.logger.info(f"Saved {len(scenarios)} scenarios to {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to save scenarios: {e}")
            
    def get_generation_stats(self) -> Dict[str, Any]:
        """
        获取生成统计信息
        
        Returns:
            统计信息
        """
        try:
            # 从保存的文件中统计
            scenario_files = self.file_manager.list_files(".", "scenarios_batch_*.json")
            
            total_scenarios = 0
            domains = set()
            
            for file_path in scenario_files:
                scenarios = self.file_manager.load_json(file_path)
                total_scenarios += len(scenarios)
                
                for scenario in scenarios:
                    domains.add(scenario.get('domain', ''))
            
            return {
                'total_scenarios': total_scenarios,
                'total_domains': len(domains),
                'batch_files': len(scenario_files),
                'domains_list': list(domains),
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get generation stats: {e}")
            return {} 