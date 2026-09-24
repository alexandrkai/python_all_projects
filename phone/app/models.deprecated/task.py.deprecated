# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/models/task.py
from ._base import BaseModel, Field,datetime, timedelta,Optional, Callable, Dict, Any, List
from enum import Enum

class TaskType(str, Enum):
    ONE_TIME = "one_time"
    PERIODIC = "periodic"
    CRON = "cron"

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskRequest(BaseModel):
    task_name: str = Field(..., description="Название задачи")
    task_type: TaskType = Field(default=TaskType.ONE_TIME)
    execute_at: Optional[datetime] = Field(None, description="Время выполнения для one_time")
    cron_expression: Optional[str] = Field(None, description="Cron выражение для cron задач")
    interval_seconds: Optional[int] = Field(None, description="Интервал в секундах для периодических задач")
    function_name: str = Field(..., description="Имя функции для выполнения")
    function_args: Optional[Dict[str, Any]] = Field(default_factory=dict)
    function_kwargs: Optional[Dict[str, Any]] = Field(default_factory=dict)
    description: Optional[str] = None
    
class TaskResponse(BaseModel):
    task_id: str
    task_name: str
    task_type: TaskType
    status: TaskStatus
    execute_at: Optional[datetime]
    created_at: datetime
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None