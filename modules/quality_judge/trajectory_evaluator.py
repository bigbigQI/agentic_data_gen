"""
轨迹评估器
评估多轮智能体交互轨迹的质量
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from core.base_module import BaseModule
from core.models import Trajectory, TrajectoryScore, Task, ConversationTurn
from core.exceptions import QualityEvaluationError
from config.prompts.evaluation_prompts import EvaluationPrompts
from utils.llm_client import LLMClient, LLMResponse
from utils.logger import setup_logger
from utils.file_manager import FileManager


class TrajectoryEvaluator(BaseModule):
    """
    轨迹评估器
    评估多轮智能体交互轨迹的质量
    """
    
    def __init__(self, config: Dict[str, Any] = None, logger: logging.Logger = None):
        """
        初始化轨迹评估器
        
        Args:
            config: 配置字典
            logger: 日志器
        """
        super().__init__(config, logger)
        self.llm_client = None
        self.file_manager = None
        self.evaluation_prompts = EvaluationPrompts()
        self.quality_config = config.get("quality_config", {}) if config else {}
        
    def _setup(self):
        """设置模块"""
        from config.settings import settings
        llm_config = self.config.get("llm_config", {})
        if not llm_config:
            raise QualityEvaluationError("LLM configuration is required for trajectory evaluation")
        
        self.llm_client = LLMClient(llm_config, self.logger)
        data_path = settings.get_data_path('trajectory_evaluations')
        self.file_manager = FileManager(data_path, self.logger)
        
        self.logger.info("TrajectoryEvaluator initialized successfully")
    
    def evaluate_trajectory(
        self, 
        trajectory: Trajectory, 
        task: Optional[Task] = None,
        **kwargs
    ) -> TrajectoryScore:
        """
        评估单个轨迹的质量
        
        Args:
            trajectory: 要评估的轨迹
            task: 对应的任务信息（可选）
            **kwargs: 额外参数
            
        Returns:
            轨迹评分结果
        """
        try:
            self.logger.info(f"Evaluating trajectory: {trajectory.id}")
            
            # 准备评估数据
            evaluation_data = self._prepare_evaluation_data(trajectory, task)
            
            # 生成评估提示词
            evaluation_prompt = self._generate_evaluation_prompt(evaluation_data)
            
            # 调用LLM进行评估
            evaluation_response = self.llm_client.generate_completion(
                prompt=evaluation_prompt,
                system_prompt=self.evaluation_prompts.TRAJECTORY_EVALUATION_SYSTEM,
                temperature=0.1,  # 低温度确保评估的一致性
            )
            
            # 解析评估结果
            evaluation_result = self._parse_evaluation_result(evaluation_response)
            
            trajectory.evaluation_score = TrajectoryScore(
                overall_score=evaluation_result.get("overall_score", 0)
            )

            self.save_trajectory_evaluation(trajectory)
            return trajectory
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate trajectory {trajectory.id}: {e}")
            raise QualityEvaluationError(f"Trajectory evaluation failed: {e}")
    
    
    def _prepare_evaluation_data(
        self, 
        trajectory: Trajectory, 
        task: Optional[Task] = None
    ) -> Dict[str, Any]:
        """
        准备评估数据
        
        Args:
            trajectory: 轨迹对象
            task: 任务对象
            
        Returns:
            评估数据字典
        """
        # 提取对话历史
        conversation_history = []
        tool_results = []
        
        for turn in trajectory.session.turns:
            turn_data = {
                "speaker": turn.speaker,
                "recipient": turn.recipient,
                "message": turn.message,
            }
            conversation_history.append(turn_data)
            
            # 提取工具执行结果
            if turn.speaker == "execution":          
                tool_results.append({
                    "result": turn.message
                })

        
        # 准备任务信息
        task_info = {}
        if task:
            task_info = {
                "description": task.description,
                "expected_tools": task.expected_tools,
                "success_criteria": task.rubric.success_criteria if task.rubric else []
            }
        
        return {
            "trajectory_id": trajectory.id,
            "task_info": task_info,
            "conversation_history": conversation_history,
            "tool_results": tool_results,
        }
    
    def _generate_evaluation_prompt(self, evaluation_data: Dict[str, Any]) -> str:
        """
        生成评估提示词
        
        Args:
            evaluation_data: 评估数据
            
        Returns:
            评估提示词
        """
        task_info = evaluation_data["task_info"]
        
        return self.evaluation_prompts.TRAJECTORY_EVALUATION_USER.format(
            task_description=task_info.get("description", ""),
            tool_usage_expectations="\n".join([f"- {expection}" for expection in task_info.get("tool_usage_expectations", [])]),
            conversation_history=json.dumps(evaluation_data["conversation_history"], indent=2, ensure_ascii=False),
            tool_results=json.dumps(evaluation_data["tool_results"], indent=2, ensure_ascii=False)
        )
    
    def _parse_evaluation_result(self, response: LLMResponse) -> Dict[str, Any]:
        """
        解析评估结果
        
        Args:
            response: LLM响应
            
        Returns:
            解析后的评估结果
        """
        try:
            evaluation_result = self.llm_client.parse_json_response(response)
            
            if "overall_score" not in evaluation_result:
                raise QualityEvaluationError(f"Missing required field in evaluation result: overall_score")
            
            # 验证分数范围
            overall_score = evaluation_result.get("overall_score", 0)
            if not 0 <= overall_score <= 5:
                raise QualityEvaluationError(f"Invalid overall score: {overall_score}")
            
            return evaluation_result
            
        except Exception as e:
            self.logger.error(f"Failed to parse evaluation result: {e}")
            raise QualityEvaluationError(f"Failed to parse evaluation result: {e}")

    def prefilter_trajectory(self, trajectory: Trajectory) -> bool:
        """
        预过滤轨迹
        
        Args:
            trajectory: 轨迹对象
            
        Returns:
            是否通过预过滤检查
        """
        # 基本结构检查
        if not trajectory.session or not trajectory.session.turns:
            self.logger.debug(f"Trajectory {trajectory.id}: No session or turns")
            return False

        # 检查至少有一次用户和智能体的交互
        user_turns = [turn for turn in trajectory.session.turns if turn.speaker == "user"]
        agent_turns = [turn for turn in trajectory.session.turns if turn.speaker == "agent"]
        
        if not user_turns or not agent_turns:
            return False

        # 获取最后一个对话轮次
        last_turn = trajectory.session.turns[-1]
        
        # 检查最后一个message是否由用户发出
        if last_turn.speaker != "user":
            return False
        
        # 检查最后一个message内容
        last_message = last_turn.message
        
        message_text = last_message.lower()
        
        
        # 检查是否包含"finish conversation"
        if "finish conversation" not in message_text:
            return False
        
        self.logger.debug(f"Trajectory {trajectory.id}: Passed prefilter checks")
        return True
    
    def save_trajectory_evaluation(
        self, 
        trajectory: Trajectory, 
    ) -> Dict[str, Any]:
        """
        保存已评估的轨迹数据
        
        Args:
            trajectory: 已评估的轨迹对象
            
        Returns:
            保存结果信息字典
        """
        try:
            training_data = trajectory.to_training_format()
            
            # 保存文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{trajectory.id}_{timestamp}.json"
            
            self.file_manager.save_json(training_data, filename)
            self.logger.info(f"Saved trajectory to {filename}")
            
            return filename
            
        except Exception as e:
            self.logger.error(f"Failed to save session: {e}")
            raise AgentDataGenException(f"Session save failed: {e}")
