"""
统一会话管理器
管理用户、智能体和工具执行器的统一对话会话
"""

import json
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from core.base_module import BaseModule
from core.models import Task, AgentConfig, UserPersona, ConversationTurn, InteractionSession, Trajectory
from core.exceptions import AgentDataGenException
from utils.data_processor import DataProcessor
from utils.file_manager import FileManager


class SessionManager(BaseModule):
    """统一会话管理器"""
    
    def __init__(self, config: Dict[str, Any] = None, logger: logging.Logger = None):
        """
        初始化统一会话管理器
        
        Args:
            config: 配置字典
            logger: 日志器
        """
        super().__init__(config, logger)
        
        self.data_processor = None
        self.file_manager = None
        
        # 当前会话状态
        self.current_session = None
        self.inference_data = ""
        
        # 配置
        self.max_turns = 20
        
    def _setup(self):
        """设置组件"""
        from config.settings import settings
        
        # 初始化数据处理器
        self.data_processor = DataProcessor(self.logger)
        
        # 初始化文件管理器
        data_path = settings.get_data_path('trajectories')
        self.file_manager = FileManager(data_path, self.logger)
        
        # 更新配置
        config = self.config or {}
        self.max_turns = config.get('max_turns', 20)
    
    def create_session(self, task: Task, agent_config: AgentConfig, user_persona: UserPersona) -> InteractionSession:
        """
        创建统一会话
        
        Args:
            task: 任务对象
            agent_config: 智能体配置
            user_persona: 用户人格
            
        Returns:
            交互会话对象
        """
        try:
            # 生成会话ID
            session_id = self.data_processor.generate_id('session', {
                'task_id': task.id,
                'agent_id': agent_config.id,
            })
            
            # 创建会话对象
            session = InteractionSession(
                id=session_id,
                task_id=task.id,
                agent_id=agent_config.id,
                session_state={
                    'persona_info': {
                        'personality_type': user_persona.personality_type.value,
                        'style_type': user_persona.style_type.value,
                        'characteristics': user_persona.metadata
                    },
                    'agent_tools': agent_config.tools,
                    'turn_count': 0
                }
            )
            
            # 设置当前会话
            self.current_session = session
            self.inference_data = ""
            
            self.logger.info(f"Created unified session: {session_id}")
            return session
            
        except Exception as e:
            self.logger.error(f"Failed to create unified session: {e}")
            raise AgentDataGenException(f"Session creation failed: {e}")
    
    def add_message(self, sender: str, recipient: str, message: str):
        """
        添加消息到对话历史
        
        Args:
            sender: 发送者 ("user", "agent", "execution")
            recipient: 接收者 ("user", "agent", "execution")
            message: 消息内容
        """
        try:
            if not self.current_session:
                raise AgentDataGenException("No active session to add message")
            
            # 创建ConversationTurn对象
            turn = ConversationTurn(
                speaker=sender,
                recipient=recipient,
                message=message,
                metadata={
                    'turn_index': len(self.current_session.turns)
                }
            )
            
            # 添加到会话
            self.current_session.turns.append(turn)
            self.current_session.session_state['turn_count'] = len(self.current_session.turns)
            
            self.logger.debug(f"Added message: {sender} -> {recipient}")
            
        except Exception as e:
            self.logger.error(f"Failed to add message: {e}")
    
    def get_last_recipient(self) -> str:
        """获取最后一条消息的接收者"""
        if not self.current_session or not self.current_session.turns:
            return "user"
        return self.current_session.turns[-1].recipient
    
    def get_last_message(self) -> Dict[str, Any]:
        """获取最后一条消息"""
        if not self.current_session or not self.current_session.turns:
            return {}
        last_turn = self.current_session.turns[-1]
        return {
            "sender": last_turn.speaker,
            "recipient": last_turn.recipient,
            "message": last_turn.message
        }
    
    def get_conversation_history(self) -> str:
        """获取格式化的对话历史"""
        try:
            if not self.current_session:
                return ""
                
            history_lines = []
            
            for turn in self.current_session.turns:
                sender = turn.speaker
                message = turn.message
                
                if sender == "user":
                    history_lines.append(f"user: {message}")
                elif sender == "agent":
                    history_lines.append(f"agent: {message}")
                elif sender == "execution":
                    # 处理执行结果的显示
                    if isinstance(message, list):
                        # 如果是执行结果列表，格式化显示
                        for result in message:
                            history_lines.append(f"execution: {json.dumps(result, ensure_ascii=False, indent=2)}")
                    else:
                        history_lines.append(f"execution: {message}")
            
            return "\n".join(history_lines)
            
        except Exception as e:
            self.logger.error(f"Failed to get conversation history: {e}")
            return ""
    
    def should_end_conversation(self) -> bool:
        """判断是否应该结束对话"""
        try:
            if not self.current_session:
                return True
            
            turn_count = len(self.current_session.turns)
            
            # 检查最大轮数
            if turn_count >= self.max_turns:
                return True
            
            # 检查是否有"finish conversation"消息
            if self.current_session.turns:
                last_message = self.current_session.turns[-1].message
                if "finish conversation" in str(last_message).lower():
                    return True
            
            return False
            
        except Exception:
            return True
    
    def finalize_session(self) -> Trajectory:
        """完成会话并生成轨迹"""
        try:
            if not self.current_session:
                raise AgentDataGenException("No active session to finalize")
            
            # 更新会话状态
            self.current_session.status = "completed"
            self.current_session.ended_at = datetime.now()
            
            # 生成轨迹ID
            trajectory_id = self.data_processor.generate_id('trajectory', {
                'session_id': self.current_session.id,
                'task_id': self.current_session.task_id,
                'agent_id': self.current_session.agent_id
            })
            
            # 创建轨迹对象
            trajectory = Trajectory(
                id=trajectory_id,
                session=self.current_session
            )
            
            self.logger.info(f"Finalized session: {self.current_session.id}")
            return trajectory
            
        except Exception as e:
            self.logger.error(f"Failed to finalize session: {e}")
            raise AgentDataGenException(f"Session finalization failed: {e}")
    
    def save_session(self, trajectory: Trajectory) -> str:
        """保存会话轨迹"""
        try:
            # 转换为训练数据格式
            training_data = trajectory.to_training_format()
            
            # 保存文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trajectory_{trajectory.id}_{timestamp}.json"
            
            self.file_manager.save_json(training_data, filename)
            self.logger.info(f"Saved trajectory to {filename}")
            
            return filename
            
        except Exception as e:
            self.logger.error(f"Failed to save session: {e}")
            raise AgentDataGenException(f"Session save failed: {e}")
