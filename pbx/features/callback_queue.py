"""
Callback Queuing System
Avoid hold time with scheduled callbacks
"""
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from enum import Enum
from pbx.utils.logger import get_logger


class CallbackStatus(Enum):
    """Callback request status"""
    PENDING = 'pending'
    SCHEDULED = 'scheduled'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class CallbackQueue:
    """System for managing callback requests"""
    
    def __init__(self, config=None):
        """Initialize callback queue"""
        self.logger = get_logger()
        self.config = config or {}
        self.enabled = self.config.get('features', {}).get('callback_queue', {}).get('enabled', False)
        
        # Configuration
        self.max_wait_time = self.config.get('features', {}).get('callback_queue', {}).get('max_wait_minutes', 30)
        self.retry_attempts = self.config.get('features', {}).get('callback_queue', {}).get('retry_attempts', 3)
        self.retry_interval = self.config.get('features', {}).get('callback_queue', {}).get('retry_interval_minutes', 5)
        
        # Callback requests
        self.callbacks = {}  # callback_id -> callback info
        self.queue_callbacks = {}  # queue_id -> list of callback_ids
        
        if self.enabled:
            self.logger.info("Callback queue system initialized")
            self.logger.info(f"  Max wait time: {self.max_wait_time} minutes")
            self.logger.info(f"  Retry attempts: {self.retry_attempts}")
    
    def request_callback(self, queue_id: str, caller_number: str, 
                        caller_name: Optional[str] = None,
                        preferred_time: Optional[datetime] = None) -> Dict:
        """
        Request a callback instead of waiting in queue
        
        Args:
            queue_id: Queue identifier
            caller_number: Caller's phone number
            caller_name: Caller's name (optional)
            preferred_time: Preferred callback time (optional, defaults to ASAP)
            
        Returns:
            Callback request information
        """
        if not self.enabled:
            return {'error': 'Callback queue not enabled'}
        
        # Generate callback ID
        callback_id = f"cb_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.callbacks)}"
        
        # Calculate estimated callback time
        if preferred_time:
            callback_time = preferred_time
        else:
            # ASAP - estimate based on queue length
            queue_length = len(self.queue_callbacks.get(queue_id, []))
            callback_time = datetime.now() + timedelta(minutes=queue_length * 5)  # 5 min per call estimate
        
        callback_info = {
            'callback_id': callback_id,
            'queue_id': queue_id,
            'caller_number': caller_number,
            'caller_name': caller_name,
            'requested_at': datetime.now(),
            'callback_time': callback_time,
            'status': CallbackStatus.SCHEDULED,
            'attempts': 0,
            'max_attempts': self.retry_attempts
        }
        
        self.callbacks[callback_id] = callback_info
        
        # Add to queue
        if queue_id not in self.queue_callbacks:
            self.queue_callbacks[queue_id] = []
        self.queue_callbacks[queue_id].append(callback_id)
        
        self.logger.info(f"Callback requested: {callback_id} for {caller_number} in queue {queue_id}")
        self.logger.info(f"  Estimated callback time: {callback_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return {
            'callback_id': callback_id,
            'estimated_time': callback_time.isoformat(),
            'queue_position': len(self.queue_callbacks[queue_id]),
            'status': 'scheduled'
        }
    
    def get_next_callback(self, queue_id: str) -> Optional[Dict]:
        """Get next callback to process for a queue"""
        if queue_id not in self.queue_callbacks or not self.queue_callbacks[queue_id]:
            return None
        
        now = datetime.now()
        
        # Find next callback that's ready
        for callback_id in self.queue_callbacks[queue_id]:
            callback = self.callbacks.get(callback_id)
            if not callback:
                continue
            
            # Check if it's time to call back
            if (callback['status'] == CallbackStatus.SCHEDULED and 
                callback['callback_time'] <= now):
                return callback
        
        return None
    
    def start_callback(self, callback_id: str, agent_id: str) -> Dict:
        """Start processing a callback"""
        if callback_id not in self.callbacks:
            return {'error': 'Callback not found'}
        
        callback = self.callbacks[callback_id]
        callback['status'] = CallbackStatus.IN_PROGRESS
        callback['agent_id'] = agent_id
        callback['started_at'] = datetime.now()
        callback['attempts'] += 1
        
        self.logger.info(f"Starting callback {callback_id} (attempt {callback['attempts']})")
        
        return {
            'callback_id': callback_id,
            'caller_number': callback['caller_number'],
            'caller_name': callback['caller_name'],
            'queue_id': callback['queue_id']
        }
    
    def complete_callback(self, callback_id: str, success: bool, 
                         notes: Optional[str] = None) -> bool:
        """Mark callback as completed"""
        if callback_id not in self.callbacks:
            return False
        
        callback = self.callbacks[callback_id]
        
        if success:
            callback['status'] = CallbackStatus.COMPLETED
            callback['completed_at'] = datetime.now()
            callback['notes'] = notes
            
            # Remove from queue
            queue_id = callback['queue_id']
            if queue_id in self.queue_callbacks:
                self.queue_callbacks[queue_id].remove(callback_id)
            
            self.logger.info(f"Callback {callback_id} completed successfully")
        else:
            # Check if we should retry
            if callback['attempts'] < callback['max_attempts']:
                callback['status'] = CallbackStatus.SCHEDULED
                callback['callback_time'] = datetime.now() + timedelta(minutes=self.retry_interval)
                self.logger.info(f"Callback {callback_id} failed, will retry at {callback['callback_time']}")
            else:
                callback['status'] = CallbackStatus.FAILED
                callback['failed_at'] = datetime.now()
                callback['notes'] = notes
                
                # Remove from queue
                queue_id = callback['queue_id']
                if queue_id in self.queue_callbacks:
                    self.queue_callbacks[queue_id].remove(callback_id)
                
                self.logger.warning(f"Callback {callback_id} failed after {callback['attempts']} attempts")
        
        return True
    
    def cancel_callback(self, callback_id: str) -> bool:
        """Cancel a pending callback"""
        if callback_id not in self.callbacks:
            return False
        
        callback = self.callbacks[callback_id]
        callback['status'] = CallbackStatus.CANCELLED
        callback['cancelled_at'] = datetime.now()
        
        # Remove from queue
        queue_id = callback['queue_id']
        if queue_id in self.queue_callbacks:
            self.queue_callbacks[queue_id].remove(callback_id)
        
        self.logger.info(f"Callback {callback_id} cancelled")
        return True
    
    def get_callback_info(self, callback_id: str) -> Optional[Dict]:
        """Get information about a callback"""
        callback = self.callbacks.get(callback_id)
        if not callback:
            return None
        
        return {
            'callback_id': callback_id,
            'queue_id': callback['queue_id'],
            'caller_number': callback['caller_number'],
            'caller_name': callback['caller_name'],
            'status': callback['status'].value,
            'requested_at': callback['requested_at'].isoformat(),
            'callback_time': callback['callback_time'].isoformat(),
            'attempts': callback['attempts']
        }
    
    def list_queue_callbacks(self, queue_id: str, status: Optional[CallbackStatus] = None) -> List[Dict]:
        """List callbacks for a queue"""
        callback_ids = self.queue_callbacks.get(queue_id, [])
        
        callbacks = []
        for callback_id in callback_ids:
            callback = self.callbacks.get(callback_id)
            if callback and (status is None or callback['status'] == status):
                callbacks.append(self.get_callback_info(callback_id))
        
        return callbacks
    
    def get_queue_statistics(self, queue_id: str) -> Dict:
        """Get callback statistics for a queue"""
        all_callbacks = [
            self.callbacks[cid] for cid in self.queue_callbacks.get(queue_id, [])
            if cid in self.callbacks
        ]
        
        return {
            'queue_id': queue_id,
            'pending_callbacks': sum(1 for c in all_callbacks if c['status'] == CallbackStatus.SCHEDULED),
            'in_progress_callbacks': sum(1 for c in all_callbacks if c['status'] == CallbackStatus.IN_PROGRESS),
            'completed_callbacks': sum(1 for c in all_callbacks if c['status'] == CallbackStatus.COMPLETED),
            'failed_callbacks': sum(1 for c in all_callbacks if c['status'] == CallbackStatus.FAILED)
        }
    
    def cleanup_old_callbacks(self, days: int = 30):
        """Clean up old completed/failed callbacks"""
        cutoff = datetime.now() - timedelta(days=days)
        
        to_remove = []
        for callback_id, callback in self.callbacks.items():
            if callback['status'] in [CallbackStatus.COMPLETED, CallbackStatus.FAILED, CallbackStatus.CANCELLED]:
                completed_at = callback.get('completed_at') or callback.get('failed_at') or callback.get('cancelled_at')
                if completed_at and completed_at < cutoff:
                    to_remove.append(callback_id)
        
        for callback_id in to_remove:
            del self.callbacks[callback_id]
        
        if to_remove:
            self.logger.info(f"Cleaned up {len(to_remove)} old callbacks")
    
    def get_statistics(self) -> Dict:
        """Get overall callback queue statistics"""
        status_counts = {}
        for callback in self.callbacks.values():
            status = callback['status'].value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            'enabled': self.enabled,
            'total_callbacks': len(self.callbacks),
            'active_queues': len(self.queue_callbacks),
            'status_breakdown': status_counts
        }
