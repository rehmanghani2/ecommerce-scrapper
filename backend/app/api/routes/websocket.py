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
from app.services.in_memory_pubsub import in_memory_pubsub

import redis.asyncio as redis
from app.services.redis_subscriber import RedisSubscriber

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
    
    redis_client = None
    pubsub = None
    redis_task = None
    
    try:
        # Subscribe to Redis channel for this user
        redis_client = redis.from_url(settings.REDIS_URL)
        pubsub = redis_client.pubsub()
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
        logger.info(f"User WebSocket {user_id} connected with Redis pub-sub")
        
    except Exception as e:
        logger.warning(f"Redis is not available for websocket {user_id}: {e}. Falling back to in-memory mode.")
        redis_task = None
        pubsub = None
        redis_client = None

    try:
        # Handle incoming messages from client
        while True:
            try:
                data = await websocket.receive_json()
                
                # Handle different message types
                message_type = data.get("type")
                
                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})
                    
                elif message_type == "subscribe" and pubsub:
                    # Subscribe to additional channels
                    channels = data.get("channels", [])
                    for channel in channels:
                        await pubsub.subscribe(channel)
                        
                elif message_type == "unsubscribe" and pubsub:
                    channels = data.get("channels", [])
                    for channel in channels:
                        await pubsub.unsubscribe(channel)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning(f"WebSocket error: {e}")
                break
        
        # Cleanup
        if redis_task:
            redis_task.cancel()
        if pubsub:
            await pubsub.unsubscribe()
        if redis_client:
            await redis_client.close()
            
    except Exception as e:
        logger.error(f"WebSocket execution error: {e}")
        
    finally:
        await websocket_manager.disconnect(user_id, websocket)


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
    
    # Define callback to send JSON data to websocket from in-memory pub-sub
    async def on_event(data: dict):
        try:
            await websocket.send_json(data)
        except Exception:
            pass

    # Subscribe to in-memory pub-sub
    await in_memory_pubsub.subscribe(f"job:{job_id}", on_event)
    
    redis_client = None
    pubsub = None
    redis_task = None
    
    try:
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
        logger.info(f"Job WebSocket {job_id} connected with Redis pub-sub")
        
    except Exception as e:
        logger.warning(f"Redis not available for job WebSocket {job_id}: {e}. Running in memory-only mode.")

    try:
        while True:
            try:
                data = await websocket.receive_json()
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                break
            except Exception:
                break
                
    finally:
        # Cleanup local subscription
        await in_memory_pubsub.unsubscribe(f"job:{job_id}", on_event)
        
        # Cleanup Redis subscription
        if redis_task:
            redis_task.cancel()
        if pubsub:
            await pubsub.unsubscribe()
        if redis_client:
            await redis_client.close()


# NEW FROM 
@router.websocket("/ws/{job_id}")
async def job_ws(websocket: WebSocket, job_id: str):
    await websocket.accept()

    async def send_to_client(message: dict):
        try:
            await websocket.send_json(message)
        except Exception:
            pass

    # Subscribe to in-memory pub-sub
    await in_memory_pubsub.subscribe(f"job:{job_id}", send_to_client)

    subscriber = None
    subscriber_task = None
    
    try:
        subscriber = RedisSubscriber()
        await subscriber.connect()
        
        async def listen_redis():
            await subscriber.subscribe(
                channel=f"job:{job_id}",
                message_handler=send_to_client
            )
            
        subscriber_task = asyncio.create_task(listen_redis())
        logger.info(f"Job ws {job_id} connected with RedisSubscriber")
        
    except Exception as e:
        logger.warning(f"RedisSubscriber failed for job_ws {job_id}: {e}. Running in memory-only mode.")

    try:
        while True:
            # Just keep connection alive and wait for client to disconnect
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await in_memory_pubsub.unsubscribe(f"job:{job_id}", send_to_client)
        if subscriber_task:
            subscriber_task.cancel()
        if subscriber:
            try:
                await subscriber.close()
            except Exception:
                pass
