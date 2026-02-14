"""
WebSocket API Routes
Real-time communication for job updates and notifications.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import asyncio
import json
import logging

from app.services.notification_service import websocket_manager
from app.config import settings

import redis.asyncio as redis



logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time updates.
    
    Clients connect to receive:
    - Job progress updates
    - Job completion notifications
    - System notifications
    """
    # Validate token (simplified - would normally verify JWT)
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return
    
    # Accept connection
    await websocket.accept()
    
    # Register connection
    await websocket_manager.connect(user_id, websocket)
    
    try:
        # Subscribe to Redis channel for this user
        
        
        redis_client = redis.from_url(settings.REDIS_URL)
        print("redis_client", redis_client)
        pubsub = redis_client.pubsub()
        print("pubsub", pubsub)
        await pubsub.subscribe(f"notifications:{user_id}")
        
        # Start listening for messages
        async def listen_redis():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await websocket.send_json(data)
                    except Exception as e:
                        logger.warning(f"Error sending WebSocket message: {e}")
        
        # Start Redis listener in background
        redis_task = asyncio.create_task(listen_redis())
        
        # Handle incoming messages from client
        while True:
            try:
                data = await websocket.receive_json()
                
                # Handle different message types
                message_type = data.get("type")
                
                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})
                    
                elif message_type == "subscribe":
                    # Subscribe to additional channels
                    channels = data.get("channels", [])
                    for channel in channels:
                        await pubsub.subscribe(channel)
                        
                elif message_type == "unsubscribe":
                    channels = data.get("channels", [])
                    for channel in channels:
                        await pubsub.unsubscribe(channel)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning(f"WebSocket error: {e}")
                break
        
        # Cleanup
        redis_task.cancel()
        await pubsub.unsubscribe()
        await redis_client.close()
        
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        
    finally:
        await websocket_manager.disconnect(user_id, websocket)

try:
    # import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

@router.websocket("/ws/jobs/{job_id}")
async def job_updates_websocket(
    websocket: WebSocket,
    job_id: str,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for job-specific updates.
    
    Subscribe to real-time updates for a specific job.
    """
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return
    
    await websocket.accept()
    
    try:
        # import redis.asyncio as redis
        
        redis_client = redis.from_url(settings.REDIS_URL)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"job:{job_id}")
        
        async def listen_redis():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await websocket.send_json(data)
                    except Exception:
                        pass
        
        redis_task = asyncio.create_task(listen_redis())
        
        while True:
            try:
                data = await websocket.receive_json()
                
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except WebSocketDisconnect:
                break
            except Exception:
                break
        
        redis_task.cancel()
        await pubsub.unsubscribe()
        await redis_client.close()
        
    except Exception as e:
        logger.error(f"Job WebSocket error: {e}")