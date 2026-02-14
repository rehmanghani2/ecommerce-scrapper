"""
Notification Service Module
Handles sending notifications to users.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import logging
import aiohttp

from app.config import settings

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """Types of notifications."""
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    EXPORT_READY = "export_ready"
    SYSTEM_ALERT = "system_alert"


class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    WEBSOCKET = "websocket"
    EMAIL = "email"
    WEBHOOK = "webhook"
    IN_APP = "in_app"


class NotificationService:
    """
    Service for sending notifications through various channels.
    
    Features:
    - WebSocket real-time notifications
    - Email notifications
    - Webhook notifications
    - In-app notifications
    """
    
    def __init__(self):
        """Initialize the notification service."""
        self._websocket_connections: Dict[int, List[Any]] = {}
        self._notification_queue: asyncio.Queue = asyncio.Queue()
    
    async def send_notification(
        self,
        user_id: int,
        notification_type: str,
        data: Dict[str, Any],
        channels: Optional[List[NotificationChannel]] = None
    ) -> bool:
        """
        Send a notification to a user.
        
        Args:
            user_id: Target user ID
            notification_type: Type of notification
            data: Notification data
            channels: Delivery channels (default: all configured)
        
        Returns:
            Success status
        """
        if channels is None:
            channels = [NotificationChannel.WEBSOCKET, NotificationChannel.IN_APP]
        
        notification = {
            "id": f"notif_{datetime.utcnow().timestamp()}",
            "user_id": user_id,
            "type": notification_type,
            "data": data,
            "created_at": datetime.utcnow().isoformat(),
            "read": False,
        }
        
        success = True
        
        for channel in channels:
            try:
                if channel == NotificationChannel.WEBSOCKET:
                    await self._send_websocket(user_id, notification)
                    
                elif channel == NotificationChannel.EMAIL:
                    await self._send_email(user_id, notification)
                    
                elif channel == NotificationChannel.WEBHOOK:
                    await self._send_webhook(user_id, notification)
                    
                elif channel == NotificationChannel.IN_APP:
                    await self._save_in_app(user_id, notification)
                    
            except Exception as e:
                logger.error(f"Failed to send notification via {channel}: {e}")
                success = False
        
        return success
    
    async def _send_websocket(self, user_id: int, notification: Dict[str, Any]) -> None:
        """Send notification via WebSocket."""
        # This would integrate with a WebSocket manager
        # For now, we'll use Redis pub/sub for real-time updates
        
        import redis.asyncio as redis
        
        try:
            redis_client = redis.from_url(settings.REDIS_URL)
            
            channel = f"notifications:{user_id}"
            message = json.dumps(notification)
            
            await redis_client.publish(channel, message)
            await redis_client.close()
            
            logger.debug(f"WebSocket notification sent to user {user_id}")
            
        except Exception as e:
            logger.error(f"WebSocket notification failed: {e}")
            raise
    
    async def _send_email(self, user_id: int, notification: Dict[str, Any]) -> None:
        """Send notification via email."""
        # Get user email from database
        from app.models.database import AsyncSessionLocal
        from app.models.user import User
        
        async with AsyncSessionLocal() as db:
            user = await db.get(User, user_id)
            if not user or not user.email:
                return
            
            # Format email based on notification type
            subject, body = self._format_email(notification)
            
            # Send email (placeholder - would integrate with email service)
            logger.info(f"Email notification sent to {user.email}: {subject}")
    
    def _format_email(self, notification: Dict[str, Any]) -> tuple:
        """Format notification for email."""
        notification_type = notification.get("type", "")
        data = notification.get("data", {})
        
        if notification_type == NotificationType.JOB_COMPLETED:
            subject = f"Scraping Job Completed: {data.get('job_name', 'Unknown')}"
            body = f"""
            Your scraping job has completed successfully!
            
            Job: {data.get('job_name', 'Unknown')}
            Products Scraped: {data.get('products_scraped', 0)}
            Duration: {data.get('duration', 0)} seconds
            
            View results at: {settings.APP_URL}/jobs/{data.get('job_id', '')}
            """
            
        elif notification_type == NotificationType.JOB_FAILED:
            subject = f"Scraping Job Failed: {data.get('job_name', 'Unknown')}"
            body = f"""
            Your scraping job has failed.
            
            Job: {data.get('job_name', 'Unknown')}
            Error: {data.get('error', 'Unknown error')}
            
            View details at: {settings.APP_URL}/jobs/{data.get('job_id', '')}
            """
            
        elif notification_type == NotificationType.EXPORT_READY:
            subject = f"Export Ready: {data.get('filename', 'export')}"
            body = f"""
            Your data export is ready for download.
            
            Filename: {data.get('filename', 'export')}
            Format: {data.get('format', 'csv')}
            Size: {data.get('size', 'Unknown')}
            
            Download at: {settings.APP_URL}/exports
            """
            
        else:
            subject = "Notification from E-Commerce Scraper"
            body = json.dumps(data, indent=2)
        
        return subject, body.strip()
    
    async def _send_webhook(self, user_id: int, notification: Dict[str, Any]) -> None:
        """Send notification via webhook."""
        # Get user's webhook URL from settings
        from app.models.database import AsyncSessionLocal
        from app.models.user import User
        
        async with AsyncSessionLocal() as db:
            user = await db.get(User, user_id)
            if not user or not user.settings:
                return
            
            try:
                user_settings = json.loads(user.settings) if isinstance(user.settings, str) else user.settings
                webhook_url = user_settings.get("webhook_url")
                
                if not webhook_url:
                    return
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        webhook_url,
                        json=notification,
                        headers={"Content-Type": "application/json"},
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status >= 400:
                            logger.warning(f"Webhook returned {response.status}")
                        else:
                            logger.debug(f"Webhook notification sent to {webhook_url}")
                            
            except Exception as e:
                logger.error(f"Webhook notification failed: {e}")
                raise
    
    async def _save_in_app(self, user_id: int, notification: Dict[str, Any]) -> None:
        """Save notification for in-app display."""
        import redis.asyncio as redis
        
        try:
            redis_client = redis.from_url(settings.REDIS_URL)
            
            # Store notification in Redis list
            key = f"notifications:inbox:{user_id}"
            
            await redis_client.lpush(key, json.dumps(notification))
            
            # Keep only last 100 notifications
            await redis_client.ltrim(key, 0, 99)
            
            # Set expiry (30 days)
            await redis_client.expire(key, 60 * 60 * 24 * 30)
            
            await redis_client.close()
            
        except Exception as e:
            logger.error(f"Failed to save in-app notification: {e}")
            raise
    
    async def get_user_notifications(
        self,
        user_id: int,
        limit: int = 50,
        unread_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get notifications for a user."""
        import redis.asyncio as redis
        
        try:
            redis_client = redis.from_url(settings.REDIS_URL)
            
            key = f"notifications:inbox:{user_id}"
            
            # Get notifications
            raw_notifications = await redis_client.lrange(key, 0, limit - 1)
            
            notifications = []
            for raw in raw_notifications:
                notification = json.loads(raw)
                if unread_only and notification.get("read"):
                    continue
                notifications.append(notification)
            
            await redis_client.close()
            
            return notifications
            
        except Exception as e:
            logger.error(f"Failed to get notifications: {e}")
            return []
    
    async def mark_as_read(
        self,
        user_id: int,
        notification_id: Optional[str] = None
    ) -> bool:
        """Mark notifications as read."""
        import redis.asyncio as redis
        
        try:
            redis_client = redis.from_url(settings.REDIS_URL)
            
            key = f"notifications:inbox:{user_id}"
            
            # Get all notifications
            raw_notifications = await redis_client.lrange(key, 0, -1)
            
            # Update read status
            updated = []
            for raw in raw_notifications:
                notification = json.loads(raw)
                if notification_id is None or notification.get("id") == notification_id:
                    notification["read"] = True
                updated.append(json.dumps(notification))
            
            # Replace list
            if updated:
                await redis_client.delete(key)
                await redis_client.rpush(key, *updated)
            
            await redis_client.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark notifications as read: {e}")
            return False
    
    async def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications."""
        notifications = await self.get_user_notifications(user_id, unread_only=True)
        return len(notifications)


# WebSocket connection manager for real-time notifications
class WebSocketManager:
    """Manages WebSocket connections for real-time notifications."""
    
    def __init__(self):
        """Initialize the WebSocket manager."""
        self._connections: Dict[int, List[Any]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, user_id: int, websocket: Any) -> None:
        """Register a WebSocket connection."""
        async with self._lock:
            if user_id not in self._connections:
                self._connections[user_id] = []
            self._connections[user_id].append(websocket)
            logger.debug(f"WebSocket connected for user {user_id}")
    
    async def disconnect(self, user_id: int, websocket: Any) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if user_id in self._connections:
                self._connections[user_id].remove(websocket)
                if not self._connections[user_id]:
                    del self._connections[user_id]
            logger.debug(f"WebSocket disconnected for user {user_id}")
    
    async def send_to_user(self, user_id: int, message: Dict[str, Any]) -> None:
        """Send message to all connections of a user."""
        async with self._lock:
            if user_id in self._connections:
                for websocket in self._connections[user_id]:
                    try:
                        await websocket.send_json(message)
                    except Exception as e:
                        logger.warning(f"Failed to send to WebSocket: {e}")
    
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connected users."""
        async with self._lock:
            for user_id, connections in self._connections.items():
                for websocket in connections:
                    try:
                        await websocket.send_json(message)
                    except Exception:
                        pass


# Singleton instance
websocket_manager = WebSocketManager()