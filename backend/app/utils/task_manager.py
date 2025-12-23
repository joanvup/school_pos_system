# backend/app/utils/task_manager.py
from pydantic import BaseModel
from typing import Dict, List, Optional

class TaskStatus(BaseModel):
    total: int = 0
    current: int = 0
    created: int = 0
    updated: int = 0
    errors: List[str] = []
    status: str = "processing" # processing, completed, error

# Almacén global de tareas (En producción se usaría Redis, aquí usaremos un dict)
import uuid

class TaskManager:
    _tasks: Dict[str, TaskStatus] = {}

    @classmethod
    def create_task(cls) -> str:
        task_id = str(uuid.uuid4())
        cls._tasks[task_id] = TaskStatus()
        return task_id

    @classmethod
    def update_task(cls, task_id: str, **kwargs):
        if task_id in cls._tasks:
            task = cls._tasks[task_id]
            for key, value in kwargs.items():
                setattr(task, key, value)

    @classmethod
    def get_task(cls, task_id: str) -> Optional[TaskStatus]:
        return cls._tasks.get(task_id)

task_manager = TaskManager()