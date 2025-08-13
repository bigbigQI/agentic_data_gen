"""
自定义异常类定义
定义系统中使用的所有异常类型
"""


class AgentDataGenException(Exception):
    """基础异常类"""
    def __init__(self, message: str, code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}


class ConfigurationError(AgentDataGenException):
    """配置错误"""
    pass


class ModelValidationError(AgentDataGenException):
    """数据模型验证错误"""
    pass


class LLMApiError(AgentDataGenException):
    """LLM API调用错误"""
    pass


class ToolExecutionError(AgentDataGenException):
    """工具执行错误"""
    pass


class ScenarioGenerationError(AgentDataGenException):
    """场景生成错误"""
    pass


class ToolDesignError(AgentDataGenException):
    """工具设计错误"""
    pass


class AgentSynthesisError(AgentDataGenException):
    """智能体合成错误"""
    pass


class TaskGenerationError(AgentDataGenException):
    """任务生成错误"""
    pass


class UserSimulationError(AgentDataGenException):
    """用户模拟错误"""
    pass


class TrajectoryGenerationError(AgentDataGenException):
    """轨迹生成错误"""
    pass


class QualityEvaluationError(AgentDataGenException):
    """质量评估错误"""
    pass


class DataStorageError(AgentDataGenException):
    """数据存储错误"""
    pass


class PipelineExecutionError(AgentDataGenException):
    """流程执行错误"""
    pass


class RegistryError(AgentDataGenException):
    """注册中心错误"""
    pass


class ValidationError(AgentDataGenException):
    """验证错误"""
    pass 