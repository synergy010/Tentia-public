"""
Worker pool system for concurrent processing of multiple user requests
"""

import asyncio
import time
from typing import Dict, Any, Callable, Awaitable, Optional
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
import traceback
from config.settings import MAX_WORKERS, WORKER_TIMEOUT
from config.logging_config import get_logger

logger = get_logger(__name__)

@dataclass
class WorkerTask:
    """Represents a task in the worker pool"""
    task_id: str
    user_id: int
    function: Callable
    args: tuple
    kwargs: dict
    created_at: datetime
    priority: int = 0
    timeout: float = WORKER_TIMEOUT

@dataclass
class WorkerResult:
    """Result from a worker task"""
    task_id: str
    user_id: int
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    completed_at: Optional[datetime] = None

class WorkerPool:
    """Async worker pool for handling concurrent requests"""
    
    def __init__(self, max_workers: int = MAX_WORKERS):
        self.max_workers = max_workers
        self.active_workers = 0
        self.task_queue = asyncio.Queue()
        self.results = {}
        self.worker_tasks = set()
        self.running = False
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'total_execution_time': 0.0,
            'average_execution_time': 0.0
        }
    
    async def start(self):
        """Start the worker pool"""
        if self.running:
            logger.warning("Worker pool already running")
            return
        
        self.running = True
        logger.info(f"Starting worker pool with {self.max_workers} workers")
        
        # Start worker tasks
        for i in range(self.max_workers):
            worker_task = asyncio.create_task(self._worker(f"worker-{i}"))
            self.worker_tasks.add(worker_task)
            worker_task.add_done_callback(self.worker_tasks.discard)
    
    async def stop(self):
        """Stop the worker pool"""
        if not self.running:
            return
        
        self.running = False
        logger.info("Stopping worker pool...")
        
        # Cancel all worker tasks
        for task in self.worker_tasks:
            task.cancel()
        
        # Wait for workers to finish
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        logger.info("Worker pool stopped")
    
    async def submit_task(self, user_id: int, function: Callable, *args, 
                         priority: int = 0, timeout: float = WORKER_TIMEOUT, **kwargs) -> str:
        """Submit a task to the worker pool"""
        task_id = f"{user_id}_{int(time.time() * 1000)}"
        
        task = WorkerTask(
            task_id=task_id,
            user_id=user_id,
            function=function,
            args=args,
            kwargs=kwargs,
            created_at=datetime.utcnow(),
            priority=priority,
            timeout=timeout
        )
        
        await self.task_queue.put(task)
        self.stats['total_tasks'] += 1
        
        logger.info(f"Task {task_id} submitted for user {user_id}")
        return task_id
    
    async def get_result(self, task_id: str, timeout: float = None) -> Optional[WorkerResult]:
        """Get result for a specific task"""
        start_time = time.time()
        
        while timeout is None or (time.time() - start_time) < timeout:
            if task_id in self.results:
                result = self.results[task_id]
                # Clean up old results
                if result.completed_at and (datetime.utcnow() - result.completed_at) > timedelta(minutes=5):
                    del self.results[task_id]
                return result
            
            await asyncio.sleep(0.1)
        
        return None
    
    async def _worker(self, worker_name: str):
        """Worker function that processes tasks from the queue"""
        logger.info(f"Worker {worker_name} started")
        
        while self.running:
            try:
                # Get task from queue with timeout
                try:
                    task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                if task is None:
                    break
                
                self.active_workers += 1
                start_time = time.time()
                
                try:
                    logger.info(f"Worker {worker_name} processing task {task.task_id}")
                    
                    # Execute the task with timeout
                    if asyncio.iscoroutinefunction(task.function):
                        result = await asyncio.wait_for(
                            task.function(*task.args, **task.kwargs),
                            timeout=task.timeout
                        )
                    else:
                        # For non-async functions, run in thread pool
                        loop = asyncio.get_event_loop()
                        result = await asyncio.wait_for(
                            loop.run_in_executor(None, task.function, *task.args, **task.kwargs),
                            timeout=task.timeout
                        )
                    
                    execution_time = time.time() - start_time
                    
                    worker_result = WorkerResult(
                        task_id=task.task_id,
                        user_id=task.user_id,
                        success=True,
                        result=result,
                        execution_time=execution_time,
                        completed_at=datetime.utcnow()
                    )
                    
                    self.results[task.task_id] = worker_result
                    self.stats['completed_tasks'] += 1
                    self.stats['total_execution_time'] += execution_time
                    
                    logger.info(f"Worker {worker_name} completed task {task.task_id} in {execution_time:.2f}s")
                    
                except asyncio.TimeoutError:
                    execution_time = time.time() - start_time
                    error_msg = f"Task {task.task_id} timed out after {task.timeout}s"
                    
                    worker_result = WorkerResult(
                        task_id=task.task_id,
                        user_id=task.user_id,
                        success=False,
                        error=error_msg,
                        execution_time=execution_time,
                        completed_at=datetime.utcnow()
                    )
                    
                    self.results[task.task_id] = worker_result
                    self.stats['failed_tasks'] += 1
                    
                    logger.error(f"Worker {worker_name} timed out on task {task.task_id}")
                    
                except Exception as e:
                    execution_time = time.time() - start_time
                    error_msg = f"Task {task.task_id} failed: {str(e)}"
                    
                    worker_result = WorkerResult(
                        task_id=task.task_id,
                        user_id=task.user_id,
                        success=False,
                        error=error_msg,
                        execution_time=execution_time,
                        completed_at=datetime.utcnow()
                    )
                    
                    self.results[task.task_id] = worker_result
                    self.stats['failed_tasks'] += 1
                    
                    logger.error(f"Worker {worker_name} failed on task {task.task_id}: {e}")
                    logger.debug(f"Traceback: {traceback.format_exc()}")
                
                finally:
                    self.active_workers -= 1
                    self.task_queue.task_done()
                    
                    # Update average execution time
                    if self.stats['completed_tasks'] > 0:
                        self.stats['average_execution_time'] = (
                            self.stats['total_execution_time'] / self.stats['completed_tasks']
                        )
                
            except Exception as e:
                logger.error(f"Worker {worker_name} encountered an error: {e}")
                logger.debug(f"Traceback: {traceback.format_exc()}")
                # Ensure worker doesn't crash completely
                await asyncio.sleep(1.0)
        
        logger.info(f"Worker {worker_name} stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker pool statistics"""
        return {
            **self.stats,
            'active_workers': self.active_workers,
            'queue_size': self.task_queue.qsize(),
            'running': self.running
        }
    
    def get_user_task_count(self, user_id: int) -> int:
        """Get number of active tasks for a specific user"""
        count = 0
        for task_id in self.results:
            if self.results[task_id].user_id == user_id:
                count += 1
        return count

class ConcurrentProcessor:
    """High-level interface for concurrent processing"""
    
    def __init__(self, max_workers: int = MAX_WORKERS):
        self.worker_pool = WorkerPool(max_workers)
        self.user_tasks = defaultdict(list)
        self.user_limits = defaultdict(int)
    
    async def start(self):
        """Start the concurrent processor"""
        await self.worker_pool.start()
    
    async def stop(self):
        """Stop the concurrent processor"""
        await self.worker_pool.stop()
    
    async def process_async(self, user_id: int, function: Callable, *args, 
                           priority: int = 0, timeout: float = WORKER_TIMEOUT, **kwargs) -> WorkerResult:
        """Process a task asynchronously and return result"""
        # Submit task
        task_id = await self.worker_pool.submit_task(
            user_id, function, *args, priority=priority, timeout=timeout, **kwargs
        )
        
        # Track user task
        self.user_tasks[user_id].append(task_id)
        
        # Wait for result
        result = await self.worker_pool.get_result(task_id, timeout=timeout + 5)
        
        # Clean up user task tracking
        if task_id in self.user_tasks[user_id]:
            self.user_tasks[user_id].remove(task_id)
        
        return result
    
    async def process_batch(self, user_id: int, functions: list, *args, 
                           priority: int = 0, timeout: float = WORKER_TIMEOUT, **kwargs) -> list[WorkerResult]:
        """Process multiple functions in batch for a user"""
        tasks = []
        
        for function in functions:
            task_id = await self.worker_pool.submit_task(
                user_id, function, *args, priority=priority, timeout=timeout, **kwargs
            )
            tasks.append(task_id)
            self.user_tasks[user_id].append(task_id)
        
        # Wait for all results
        results = []
        for task_id in tasks:
            result = await self.worker_pool.get_result(task_id, timeout=timeout + 5)
            results.append(result)
            
            # Clean up
            if task_id in self.user_tasks[user_id]:
                self.user_tasks[user_id].remove(task_id)
        
        return results
    
    def set_user_limit(self, user_id: int, max_concurrent: int):
        """Set maximum concurrent tasks for a user"""
        self.user_limits[user_id] = max_concurrent
    
    def can_process_user(self, user_id: int) -> bool:
        """Check if user can submit more tasks"""
        current_tasks = len(self.user_tasks[user_id])
        max_tasks = self.user_limits.get(user_id, 3)  # Default limit of 3
        return current_tasks < max_tasks
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get statistics for a specific user"""
        return {
            'active_tasks': len(self.user_tasks[user_id]),
            'task_limit': self.user_limits.get(user_id, 3),
            'can_submit': self.can_process_user(user_id)
        }
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global processing statistics"""
        return self.worker_pool.get_stats()

# Create global instances
concurrent_processor = ConcurrentProcessor()
