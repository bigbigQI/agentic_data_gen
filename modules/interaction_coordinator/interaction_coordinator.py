"""
交互协调器
负责协调整个多智能体数据生成流程
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from core.base_module import BaseModule
from core.models import Task, AgentConfig, Trajectory
from core.exceptions import AgentDataGenException
from utils.data_processor import DataProcessor
from .session_manager import SessionManager
from modules.user_simulator import UserSimulator
from modules.agent_simulator import AgentSimulator
from modules.tool_execution import ToolExecutionSimulator


class InteractionCoordinator(BaseModule):
    """交互协调器"""
    
    def __init__(self, config: Dict[str, Any] = None, logger: logging.Logger = None):
        """
        初始化交互协调器
        
        Args:
            config: 配置字典
            logger: 日志器
        """
        super().__init__(config, logger)
        
        self.data_processor = None
        
        # 组件
        self.session_manager = None
        self.user_simulator = None
        self.agent_simulator = None
        self.tool_execution_simulator = None
        
        # 配置
        self.max_turns = 20
        
    def _setup(self):
        """设置组件"""
        from config.settings import settings
        
        # 初始化数据处理器
        self.data_processor = DataProcessor(self.logger)
        
        # 初始化子模块
        self.session_manager = SessionManager(logger=self.logger)
        self.session_manager.initialize()
        
        self.user_simulator = UserSimulator(logger=self.logger)
        self.user_simulator.initialize()
        
        self.agent_simulator = AgentSimulator(logger=self.logger)
        self.agent_simulator.initialize()
        
        self.tool_execution_simulator = ToolExecutionSimulator(logger=self.logger)
        self.tool_execution_simulator.initialize()
        
        # 更新配置
        config = self.config or {}
        self.max_turns = config.get('max_turns', 20)
    
    def execute_single_interaction(self, task: Task, agent_config: AgentConfig, tools_info: Dict[str, Any]) -> Trajectory:
        """
        执行单个交互会话
        
        Args:
            task: 任务对象
            agent_config: 智能体配置
            tools_info: 工具信息
            
        Returns:
            交互轨迹
        """
        try:
            self.logger.info(f"Executing interaction: Task {task.id} with Agent {agent_config.id}")
            
            # 生成用户人格
            user_persona = self.user_simulator.persona_generator.process()
            print("user_persona", user_persona)
            # 创建统一会话
            session = self.session_manager.create_session(task, agent_config, user_persona)
            
            # 初始化各个模拟器
            self.user_simulator.initialize_for_task(task, user_persona)
            self.agent_simulator.initialize_for_agent(agent_config, tools_info)
            self.tool_execution_simulator.initialize_tools(tools_info)
            
            # 生成初始用户消息
            init_message = self.user_simulator.generate_initial_message()
            print("init_message", init_message)
            import time 
            time.sleep(10)
            # 添加初始消息到会话
            self.session_manager.add_message("user", "agent", init_message)
            
            # 执行多轮对话循环
            self._execute_conversation_loop()
            
            # 完成会话
            trajectory = self.session_manager.finalize_session()
            
            # 保存会话
            self.session_manager.save_session(trajectory)
            
            # 保存对话历史文件
            self.session_manager.write_dialogue_history(task.id, agent_config.id)
            
            self.logger.info(f"Interaction completed: {trajectory.id}")
            return trajectory
            
        except Exception as e:
            self.logger.error(f"Single interaction failed: {e}")
            raise AgentDataGenException(f"Interaction execution failed: {e}")
    
    def _execute_conversation_loop(self):
        """
        执行对话循环
        参考other_project_fils中的对话循环逻辑
        """
        try:
            turn_count = 0
            
            while turn_count < self.max_turns:
                turn_count += 1
                
                # 获取最后一条消息的接收者，决定下一个发言者
                last_recipient = self.session_manager.get_last_recipient()
                print("last_recipient", last_recipient)
                if last_recipient == "user":
                    # 轮到用户发言，调用用户模拟器
                    last_message = self.session_manager.get_last_message()
                    conversation_history = self.session_manager.get_conversation_history()
                    
                    user_response = self.user_simulator.respond_to_agent(
                        last_message.get("message", ""),
                        conversation_history
                    )
                    
                    # 检查是否结束对话
                    if "finish conversation" in user_response.lower():
                        self.session_manager.add_message("user", "agent", user_response)
                        self.logger.info("User indicated conversation completion")
                        break
                    
                    self.session_manager.add_message("user", "agent", user_response)
                    
                elif last_recipient == "agent":
                    # 轮到智能体发言，调用智能体模拟器
                    history_messages = self.session_manager.get_conversation_history()
                    print("history_messages", history_messages)
                    current_message = self.agent_simulator.respond(history_messages)
                    
                    self.session_manager.add_message(
                        current_message["sender"],
                        current_message["recipient"],
                        current_message["message"]
                    )
                    print('agent message', current_message)
                    
                else:  # last_recipient == "execution"
                    # 轮到工具执行，调用工具执行模拟器
                    last_message = self.session_manager.get_last_message()
                    execution_results = self.tool_execution_simulator.execute_agent_message(
                        last_message.get("message", "")
                    )
                    
                    self.session_manager.add_message("execution", "agent", execution_results)
                
                # 检查是否应该结束对话
                if self.session_manager.should_end_conversation():
                    break
            
            self.logger.info(f"Conversation completed after {turn_count} turns")
            
        except Exception as e:
            self.logger.error(f"Conversation loop failed: {e}")
            raise AgentDataGenException(f"Conversation execution failed: {e}")
    
    def get_coordinator_stats(self) -> Dict[str, Any]:
        """获取协调器统计信息"""
        stats = {
            'max_turns': self.max_turns,
            'module_name': self.__class__.__name__,
            'initialized': self._initialized,
            'timestamp': datetime.now().isoformat()
        }
        
        # 添加子模块统计
        if self.tool_execution_simulator:
            execution_stats = self.tool_execution_simulator.get_execution_stats()
            stats['execution_stats'] = execution_stats
        
        if self.session_manager:
            session_summary = self.session_manager.get_session_summary()
            stats['session_summary'] = session_summary
        
        return stats
