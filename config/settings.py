"""
全局配置设置
包含所有模块的配置参数
"""

import os
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv


class Settings:
    """全局配置类"""
    
    def __init__(self):
        # 项目根目录
        self.ROOT_DIR = Path(__file__).parent.parent
        self.DATA_DIR = self.ROOT_DIR / "data"
        
        # 加载 .env 文件
        env_file = self.ROOT_DIR / ".env"
        if env_file.exists():
            load_dotenv(env_file)
        # API配置
        self.LLM_CONFIG = {
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY", ""),
                "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                "model": os.getenv("OPENAI_MODEL", "gpt-4"),
                "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
                "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "2000")),
                "timeout": int(os.getenv("OPENAI_TIMEOUT", "30"))
            },
        }
        
        # 默认使用的LLM提供商
        self.DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
        
        # 数据路径配置
        self.DATA_PATHS = {
            "scenarios": self.DATA_DIR / "generated" / "scenarios",
            "tools": self.DATA_DIR / "generated" / "tools", 
            "agents": self.DATA_DIR / "generated" / "agents",
            "tasks": self.DATA_DIR / "generated" / "tasks",
            "user_personas": self.DATA_DIR / "generated" / "user_personas",
            "trajectories": self.DATA_DIR / "generated" / "trajectories",
            "high_quality_trajectories": self.DATA_DIR / "filtered" / "high_quality_trajectories",
            "training_data": self.DATA_DIR / "filtered" / "training_data",
            "temp": self.DATA_DIR / "temp",
            "cache": self.DATA_DIR / "temp" / "cache"
        }
        
        # 生成配置（支持环境变量覆盖）
        self.GENERATION_CONFIG = {
            "scenarios": {
                "target_count": int(os.getenv("SCENARIO_TARGET_COUNT", "50")),
                # "domains": [
                #     "外卖配送", "社交媒体", "金融交易", "软件应用", "机器人控制",
                #     "电商购物", "在线教育", "医疗健康", "旅游出行", "智能家居",ß
                #     "企业办公", "内容创作", "游戏娱乐", "新闻媒体", "客户服务"
                # ],
                "domains": [
                    "food_delivery",
                    "robot_control",
                    "social_media",
                    "ecommerce",
                    "travel",
                    ],
                "batch_size": int(os.getenv("SCENARIO_BATCH_SIZE", "10"))
            },
            # "tools": {
            #     "target_count": int(os.getenv("TOOL_TARGET_COUNT", "3000")),
            #     "tools_per_scenario": int(os.getenv("TOOLS_PER_SCENARIO", "8")),
            #     "max_parameters_per_tool": int(os.getenv("MAX_PARAMETERS_PER_TOOL", "6")),
            #     "batch_size": int(os.getenv("TOOL_BATCH_SIZE", "20"))
            # },
            "tools": {
                "tools_per_scenario": int(os.getenv("TOOLS_PER_SCENARIO", "10")),
                "batch_size": int(os.getenv("TOOL_BATCH_SIZE", "5"))
            },
            "agents": {
                "target_count": int(os.getenv("AGENT_TARGET_COUNT", "1000")),
                "tools_per_agent": {
                    "min": int(os.getenv("AGENT_MIN_TOOLS", "3")), 
                    "max": int(os.getenv("AGENT_MAX_TOOLS", "6"))
                },
                "batch_size": int(os.getenv("AGENT_BATCH_SIZE", "50"))
            },
            "tasks": {
                "tasks_per_difficulty": 1,
                "max_workers": 64
            },
            "user_personas": {
                "target_count": int(os.getenv("USER_PERSONA_TARGET_COUNT", "500")),
                "personality_types": [
                    "friendly", "impatient", "cautious", "casual"
                ],
                "interaction_styles": [
                    "formal", "informal", "life_oriented"
                ],
                "batch_size": int(os.getenv("USER_PERSONA_BATCH_SIZE", "25"))
            },
            "trajectories": {
                "max_count": int(os.getenv("TRAJECTORY_MAX_COUNT", "1000")),
                "max_workers": int(os.getenv("TRAJECTORY_MAX_WORKERS", "64")),
                "max_turns": int(os.getenv("TRAJECTORY_MAX_TURNS", "20"))
            }
        }
        
        # 质量评估配置（支持环境变量覆盖）
        self.QUALITY_CONFIG = {
            "score_thresholds": {
                "pass_threshold": float(os.getenv("QUALITY_PASS_THRESHOLD", "4.0")),
                "high_quality_threshold": float(os.getenv("QUALITY_HIGH_THRESHOLD", "4.5"))
            },
            "scoring_weights": {
                "task_completion": 0.4,
                "tool_usage": 0.3,
                "interaction_quality": 0.3
            },
            "evaluation_criteria": {
                "task_completion": [
                    "任务目标是否明确达成",
                    "解决方案是否合理有效",
                    "是否处理了所有必要步骤"
                ],
                "tool_usage": [
                    "工具调用是否正确",
                    "工具选择是否合适",
                    "参数传递是否准确"
                ],
                "interaction_quality": [
                    "对话是否自然流畅",
                    "响应是否及时恰当",
                    "错误处理是否得当"
                ]
            }
        }
        
        # 模拟器配置
        self.SIMULATOR_CONFIG = {
            "success_rate": float(os.getenv("SIMULATOR_SUCCESS_RATE", "0.85")),     # 工具执行成功率
            "partial_failure_rate": float(os.getenv("SIMULATOR_PARTIAL_FAILURE_RATE", "0.10")),  # 部分失败率
            "complete_failure_rate": float(os.getenv("SIMULATOR_COMPLETE_FAILURE_RATE", "0.05")),  # 完全失败率
            "state_persistence": True  # 是否持久化状态
        }
        
        # 日志配置
        self.LOGGING_CONFIG = {
            "level": os.getenv("LOG_LEVEL", "INFO"),
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file_path": self.ROOT_DIR / "logs" / "agent_data_gen.log",
            "max_size": "10MB",
            "backup_count": 5
        }
        
        # 并发配置
        self.CONCURRENCY_CONFIG = {
            "max_workers": int(os.getenv("MAX_WORKERS", "4")),
            "batch_processing": True,
            "timeout": int(os.getenv("PROCESSING_TIMEOUT", "300"))
        }
        
        # 创建必要的目录
        self._create_directories()
    
    def _create_directories(self):
        """创建必要的数据目录"""
        for path in self.DATA_PATHS.values():
            path.mkdir(parents=True, exist_ok=True)
        
        # 创建日志目录
        log_dir = self.ROOT_DIR / "logs"
        log_dir.mkdir(exist_ok=True)
    
    def get_llm_config(self, provider: str = None) -> Dict[str, Any]:
        """获取LLM配置"""
        provider = provider or self.DEFAULT_LLM_PROVIDER
        return self.LLM_CONFIG.get(provider, self.LLM_CONFIG["openai"])
    
    def get_data_path(self, data_type: str) -> Path:
        """获取数据存储路径"""
        return self.DATA_PATHS.get(data_type, self.DATA_DIR)
    
    def update_config(self, section: str, updates: Dict[str, Any]):
        """更新配置"""
        if hasattr(self, section):
            config = getattr(self, section)
            if isinstance(config, dict):
                config.update(updates)
            else:
                raise ValueError(f"Config section {section} is not a dictionary")
        else:
            raise ValueError(f"Config section {section} does not exist")


# 创建全局配置实例
settings = Settings() 