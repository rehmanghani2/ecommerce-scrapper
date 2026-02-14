# backend/app/services/websocket_service.py
from fastapi import WebSocket
from typing import Dict, Set, Optional
import asyncio
import redis.asyncio as redis

from app.config import settings

class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._redis: Optional[redis.Redis] = None
        self._subscriber_task: Optional[asyncio.Task] = None
    
    async def get_redis(self) -> redis.Redis:
        """Get Redis connection"""
        if self._redis is None:
            self._redis = redis.from_url(settings.REDIS_URL)
        return self._redis
    
    async def connect(self, websocket: WebSocket, job_id: str):
        """Accept new WebSocket connection"""
        await websocket.accept()
        
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
        
        self.active_connections[job_id].add(websocket)
        
        # Start Redis subscriber if not running
        if self._subscriber_task is None or self._subscriber_task.done():
            self._subscriber_task = asyncio.create_task(self._redis_subscriber())
    
    def disconnect(self, websocket: WebSocket, job_id: str):
        """Remove WebSocket connection"""
        if job_id in self.active_connections:
            self.active_connections[job_id].discard(websocket)
            
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
    
    async def send_to_job(self, job_id: str, message: dict):
        """Send message to all connections for a specific job"""
        if job_id in self.active_connections:
            disconnected = set()
            
            for websocket in self.active_connections[job_id]:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.add(websocket)
            
            # Clean up disconnected
            for ws in disconnected:
                self.active_connections[job_id].discard(ws)
    
    async def broadcast(self, message: dict):
        """Broadcast to all connections"""
        for job_id in list(self.active_connections.keys()):
            await self.send_to_job(job_id, message)
    
    async def _redis_subscriber(self):
        """Subscribe to Redis for job updates"""
        try:
            redis_client = await self.get_redis()
            pubsub = redis_client.pubsub()
            
            # Subscribe to all job channels
            await pubsub.psubscribe("job:*")
            
            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    channel = message["channel"].decode()
                    
                    # Extract job_id from channel (format: job:{job_id})
                    if channel.startswith("job:"):
                        job_id = channel.split(":")[1]
                        
                        try:
                            data = eval(message["data"].decode())
                            await self.send_to_job(job_id, data)
                        except:
                            pass
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Redis subscriber error: {e}")
            await asyncio.sleep(5)
            # Restart subscriber
            self._subscriber_task = asyncio.create_task(self._redis_subscriber())

# Global instance
ws_manager = WebSocketManager()