"""
核心数据模型定义
定义系统中使用的所有数据结构
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from enum import Enum
import json
from datetime import datetime


class DifficultyLevel(Enum):
    """任务难度级别"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class TaskType(Enum):
    """任务类型"""
    SINGLE_TURN = "single_turn"
    MULTI_TURN = "multi_turn"


class UserPersonalityType(Enum):
    """用户人格类型"""
    FRIENDLY = "friendly"
    IMPATIENT = "impatient"
    CAUTIOUS = "cautious"
    CURIOUS = "curious"
    CASUAL = "casual"


class InteractionStyle(Enum):
    """交互风格"""
    FORMAL = "formal"
    INFORMAL = "informal"
    LIFE_ORIENTED = "life_oriented"


@dataclass
class Scenario:
    """场景数据模型"""
    id: str
    name: str
    description: str
    domain: str
    category: str
    context: str
    use_cases: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ToolParameter:
    """工具参数"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None


@dataclass
class Tool:
    """工具数据模型"""
    id: str
    name: str
    description: str
    category: str
    scenario_ids: List[str] = field(default_factory=list)
    parameters: List[ToolParameter] = field(default_factory=list)
    return_type: str = "dict"
    examples: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_function_schema(self) -> Dict[str, Any]:
        """转换为函数调用的schema格式"""
        properties = {}
        required = []
        
        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                properties[param.name]["enum"] = param.enum
            if param.required:
                required.append(param.name)
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }


@dataclass
class AgentConfig:
    """智能体配置"""
    id: str
    system_prompt: str
    tools: List[str] = field(default_factory=list)  # tool_ids
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TaskRubric:
    """任务评分标准"""
    success_criteria: List[str] = field(default_factory=list)
    tool_usage_expectations: List[str] = field(default_factory=list)
    checkpoints: List[str] = field(default_factory=list)


@dataclass
class Task:
    """任务数据模型"""
    id: str
    agent_id: str
    title: str
    description: str
    difficulty: DifficultyLevel
    task_type: TaskType
    expected_tools: List[str] = field(default_factory=list)
    rubric: TaskRubric = field(default_factory=TaskRubric)
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class UserPersona:
    """用户人格模型"""
    id: str
    name: str
    personality_type: UserPersonalityType
    style_type: InteractionStyle
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ConversationTurn:
    """对话轮次"""
    speaker: str  # "user", "agent", "execution"
    recipient: str  # "user", "agent", "execution"
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InteractionSession:
    """交互会话"""
    id: str
    task_id: str
    agent_id: str
    turns: List[ConversationTurn] = field(default_factory=list)
    session_state: Dict[str, Any] = field(default_factory=dict)
    status: str = "active"  # active, completed, failed
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrajectoryScore:
    """轨迹评分"""
    overall_score: float
    task_completion_score: float
    tool_usage_score: float
    interaction_quality_score: float
    detailed_scores: Dict[str, float] = field(default_factory=dict)
    feedback: str = ""
    pass_threshold: float = 4.0
    
    @property
    def passed(self) -> bool:
        return self.overall_score >= self.pass_threshold


@dataclass
class Trajectory:
    """完整的交互轨迹"""
    id: str
    session: InteractionSession
    evaluation_score: Optional[TrajectoryScore] = None
    quality_tags: List[str] = field(default_factory=list)
    is_high_quality: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_training_format(self) -> Dict[str, Any]:
        """转换为训练数据格式"""
        messages = []
        for turn in self.session.turns:
            if turn.speaker == "user":
                messages.append({
                    "role": "user", 
                    "content": turn.message,
                    "recipient": turn.recipient
                })
            elif turn.speaker == "agent":
                messages.append({
                    "role": "assistant", 
                    "content": turn.message,
                    "recipient": turn.recipient
                })
            elif turn.speaker == "execution":
                messages.append({
                    "role": "execution",
                    "content": turn.message,
                    "recipient": turn.recipient
                })
        
        return {
            "trajectory_id": self.id,
            "task_id": self.session.task_id,
            "agent_id": self.session.agent_id,
            "messages": messages,
            "score": self.evaluation_score.overall_score if self.evaluation_score else None,
            "metadata": {
                "quality_tags": self.quality_tags,
                "is_high_quality": self.is_high_quality,
                "session_metadata": self.session.metadata
            }
        }


# 工具类函数
def serialize_dataclass(obj) -> str:
    """序列化dataclass对象为JSON字符串"""
    if hasattr(obj, '__dataclass_fields__'):
        # 处理dataclass
        data = {}
        for field_name, field_def in obj.__dataclass_fields__.items():
            value = getattr(obj, field_name)
            if isinstance(value, datetime):
                data[field_name] = value.isoformat()
            elif isinstance(value, Enum):
                data[field_name] = value.value
            elif hasattr(value, '__dataclass_fields__'):
                data[field_name] = serialize_dataclass(value)
            elif isinstance(value, list):
                data[field_name] = [serialize_dataclass(item) if hasattr(item, '__dataclass_fields__') else item for item in value]
            else:
                data[field_name] = value
        return json.dumps(data, ensure_ascii=False, indent=2)
    return json.dumps(obj, ensure_ascii=False, indent=2)


def deserialize_dataclass(cls, data: Union[str, dict]):
    """从JSON字符串或字典反序列化dataclass对象"""
    if isinstance(data, str):
        data = json.loads(data)
    
    # 这里需要根据具体的类来实现反序列化逻辑
    # 简化实现，实际项目中可能需要更复杂的处理
    return cls(**data) 