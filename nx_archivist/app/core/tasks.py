import time
import uuid
from enum import Enum
from typing import Dict, Optional, List
from pydantic import BaseModel

class TaskStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PACKING = "packing"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskInfo(BaseModel):
    id: str
    name: str
    status: TaskStatus
    progress: float = 0.0  # 0.0 to 100.0
    speed: float = 0.0     # bytes/s
    seeds: int = 0
    total_size: int = 0    # bytes
    eta: float = 0.0       # seconds
    error: Optional[str] = None
    start_time: float
    updated_at: float

class TaskManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskManager, cls).__new__(cls)
            cls._instance.tasks = {}
        return cls._instance

    def create_task(self, name: str) -> str:
        task_id = str(uuid.uuid4())[:8]
        now = time.time()
        self.tasks[task_id] = TaskInfo(
            id=task_id,
            name=name,
            status=TaskStatus.PENDING,
            start_time=now,
            updated_at=now
        )
        return task_id

    def update_task(self, task_id: str, **kwargs):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            task.updated_at = time.time()

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        return self.tasks.get(task_id)

    def get_active_tasks(self) -> List[TaskInfo]:
        return [t for t in self.tasks.values() if t.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]]

    def cleanup_completed(self, max_age_seconds: int = 3600):
        now = time.time()
        to_delete = []
        for tid, task in self.tasks.items():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                if now - task.updated_at > max_age_seconds:
                    to_delete.append(tid)
        for tid in to_delete:
            del self.tasks[tid]

task_manager = TaskManager()
