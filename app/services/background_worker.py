"""Background Worker for Document Processing"""
import asyncio
from typing import Dict, Callable, Any
from datetime import datetime
import uuid
import threading


class BackgroundWorker:
    """Simple background worker for async document processing"""
    
    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
        self.task_status: Dict[str, Dict[str, Any]] = {}
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
    
    def _run_loop(self):
        """Run the event loop in a separate thread"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    async def _process_task(self, task_id: str, coro):
        """Process a task and update status"""
        try:
            self.task_status[task_id] = {
                "status": "processing",
                "started_at": datetime.utcnow().isoformat(),
                "progress": 0
            }
            result = await coro
            self.task_status[task_id] = {
                "status": "completed",
                "started_at": self.task_status[task_id]["started_at"],
                "completed_at": datetime.utcnow().isoformat(),
                "progress": 100,
                "result": result
            }
            return result
        except Exception as e:
            self.task_status[task_id] = {
                "status": "failed",
                "started_at": self.task_status[task_id]["started_at"],
                "failed_at": datetime.utcnow().isoformat(),
                "error": str(e)
            }
            raise
    
    def submit_task(self, coro) -> str:
        """Submit a task to the background worker"""
        task_id = str(uuid.uuid4())
        
        async def _submit():
            task = asyncio.create_task(self._process_task(task_id, coro))
            self.tasks[task_id] = task
            return await task
        
        # Schedule the task on the background loop
        future = asyncio.run_coroutine_threadsafe(_submit(), self.loop)
        return task_id
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a task"""
        return self.task_status.get(task_id, {"status": "not_found"})
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        if task_id in self.tasks:
            self.tasks[task_id].cancel()
            self.task_status[task_id] = {
                "status": "cancelled",
                "cancelled_at": datetime.utcnow().isoformat()
            }
            return True
        return False


# Global background worker instance
background_worker = BackgroundWorker()
