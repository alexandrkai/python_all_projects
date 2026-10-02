# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/core/scheduler.py
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import croniter
import inspect
from core.log.log import logger
from concurrent.futures import ThreadPoolExecutor

@dataclass
class ScheduledTask:
    task_id: str
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    execute_at: Optional[datetime] = None
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    is_async: bool = False
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def should_run(self) -> bool:
        """Проверяет, нужно ли запускать задачу"""
        if self.status in ["running", "completed", "cancelled"]:
            return False
        
        if self.execute_at and datetime.now() >= self.execute_at:
            return True
            
        if self.cron_expression:
            cron = croniter.croniter(self.cron_expression, self.created_at)
            next_time = cron.get_next(datetime)
            return datetime.now() >= next_time
            
        return False
    
    def get_next_run(self) -> Optional[datetime]:
        """Возвращает время следующего запуска"""
        if self.cron_expression:
            cron = croniter.croniter(self.cron_expression, self.created_at)
            return cron.get_next(datetime)
        elif self.interval_seconds:
            return datetime.now() + timedelta(seconds=self.interval_seconds)
        return self.execute_at

class TaskScheduler:
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.running = False
        self._task = None
        
    def register_function(self, func: Callable, name: Optional[str] = None):
        """Регистрирует функцию для вызова по имени"""
        func_name = name or func.__name__
        self.available_functions[func_name] = func
        
    async def start(self):
        """Запускает планировщик"""
        if self.running:
            return
            
        self.running = True
        logger.info("ℹ️Планирощик задач стартовал")
        self._task = asyncio.create_task(self._run_scheduler())
        
    async def stop(self):
        """Останавливает планировщик"""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.executor.shutdown(wait=False)
        logger.info("ℹ️Планирощик задач остановлен")
        
    def schedule_task(
        self,
        name: str,
        func: Callable,
        execute_at: Optional[datetime] = None,
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None
    ) -> str:
        """Планирует новую задачу"""
        task_id = str(uuid.uuid4())
        
        # Проверяем тип функции
        is_async = inspect.iscoroutinefunction(func)
        
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs or {},
            execute_at=execute_at,
            cron_expression=cron_expression,
            interval_seconds=interval_seconds,
            is_async=is_async
        )
        
        self.tasks[task_id] = task
        logger.info(f"❌Task '{name}' scheduled with id: {task_id}")
        
        return task_id
    
    def schedule_one_time(
        self,
        name: str,
        func: Callable,
        execute_at: datetime,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None
    ) -> str:
        """Планирует разовую задачу на конкретное время"""
        return self.schedule_task(
            name=name,
            func=func,
            execute_at=execute_at,
            args=args,
            kwargs=kwargs
        )
    
    def schedule_periodic(
        self,
        name: str,
        func: Callable,
        interval_seconds: int,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None
    ) -> str:
        """Планирует периодическую задачу"""
        return self.schedule_task(
            name=name,
            func=func,
            interval_seconds=interval_seconds,
            execute_at=datetime.now() + timedelta(seconds=interval_seconds),
            args=args,
            kwargs=kwargs
        )
    
    def schedule_cron(
        self,
        name: str,
        func: Callable,
        cron_expression: str,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None
    ) -> str:
        """Планирует задачу по cron выражению"""
        # Валидация cron выражения
        try:
            croniter.croniter(cron_expression)
        except Exception as e:
            error_message= f"⚠️Invalid cron expression: {e}"
            logger.error(error_message)
            raise ValueError(error_message)
            
        return self.schedule_task(
            name=name,
            func=func,
            cron_expression=cron_expression,
            execute_at=datetime.now(),  # Первый запуск сразу
            args=args,
            kwargs=kwargs
        )
    
    def cancel_task(self, task_id: str) -> bool:
        """Отменяет задачу"""
        if task_id in self.tasks:
            self.tasks[task_id].status = "cancelled"
            logger.info(f"❌Task {task_id} cancelled")
            return True
        return False
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Получает задачу по ID"""
        return self.tasks.get(task_id)
    
    def list_tasks(self, status: Optional[str] = None) -> List[ScheduledTask]:
        """Возвращает список задач"""
        if status:
            return [task for task in self.tasks.values() if task.status == status]
        return list(self.tasks.values())
    
    async def _run_scheduler(self):
        """Основной цикл планировщика"""
        while self.running:
            try:
                current_time = datetime.now()
                
                for task in list(self.tasks.values()):
                    if task.should_run():
                        asyncio.create_task(self._execute_task(task))
                
                # Очищаем старые завершенные задачи (старше 1 часа)
                self._cleanup_old_tasks()
                
            except Exception as e:
                logger.error(f"⚠️Scheduler error: {e}")
            
            await asyncio.sleep(1)  # Проверяем каждую секунду
    
    async def _execute_task(self, task: ScheduledTask):
        """Выполняет задачу"""
        task.status = "running"
        
        try:
            if task.is_async:
                # Асинхронная функция
                task.result = await task.func(*task.args, **task.kwargs)
            else:
                # Синхронная функция запускаем в отдельном потоке
                loop = asyncio.get_event_loop()
                task.result = await loop.run_in_executor(
                    self.executor,
                    task.func,
                    *task.args,
                    **task.kwargs
                )
            
            task.status = "completed"
            logger.info(f"❌Task '{task.name}' completed successfully")
            
            # Планируем следующий запуск для периодических задач
            if task.cron_expression or task.interval_seconds:
                task.status = "pending"
                task.execute_at = task.get_next_run()
                
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            logger.error(f"⚠️Task '{task.name}' failed: {e}")
    
    def _cleanup_old_tasks(self, max_age_hours: int = 1):
        """Очищает старые завершенные задачи"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        tasks_to_remove = [
            task_id for task_id, task in self.tasks.items()
            if task.status in ["completed", "cancelled", "failed"] 
            and task.created_at < cutoff_time
        ]
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            
# Добавьте в TaskScheduler
def save_tasks(self, filepath: str):
    import pickle
    with open(filepath, 'wb') as f:
        pickle.dump(self.tasks, f)

def load_tasks(self, filepath: str):
    import pickle
    with open(filepath, 'rb') as f:
        self.tasks = pickle.load(f)

# Глобальный экземпляр планировщика
scheduler = TaskScheduler()