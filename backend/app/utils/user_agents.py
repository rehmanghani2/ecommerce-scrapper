"""
User Agent Rotation Module
Provides realistic user agents for scraping to avoid detection.
"""

import random
from typing import List, Optional, Dict
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DeviceType(str, Enum):
    """Device types for user agent selection."""
    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"


class BrowserType(str, Enum):
    """Browser types for user agent selection."""
    CHROME = "chrome"
    FIREFOX = "firefox"
    SAFARI = "safari"
    EDGE = "edge"


@dataclass
class UserAgentInfo:
    """Information about a user agent."""
    user_agent: str
    device_type: DeviceType
    browser_type: BrowserType
    platform: str
    viewport: Dict[str, int]


class UserAgentRotator:
    """
    Manages and rotates user agents for web scraping.
    Provides realistic, up-to-date user agents to avoid detection.
    """
    
    # Modern Chrome User Agents (2024)
    CHROME_DESKTOP = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    
    # Modern Firefox User Agents
    FIREFOX_DESKTOP = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    ]
    
    # Safari User Agents
    SAFARI_DESKTOP = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    ]
    
    # Edge User Agents
    EDGE_DESKTOP = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    ]
    
    # Mobile User Agents
    CHROME_MOBILE = [
        "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/121.0.6167.66 Mobile/15E148 Safari/604.1",
    ]
    
    SAFARI_MOBILE = [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPad; CPU OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    ]
    
    # Viewport sizes for different devices
    VIEWPORTS = {
        DeviceType.DESKTOP: [
            {"width": 1920, "height": 1080},
            {"width": 1536, "height": 864},
            {"width": 1440, "height": 900},
            {"width": 1366, "height": 768},
            {"width": 1280, "height": 720},
        ],
        DeviceType.MOBILE: [
            {"width": 390, "height": 844},   # iPhone 14
            {"width": 393, "height": 873},   # Pixel 7
            {"width": 360, "height": 800},   # Samsung Galaxy
            {"width": 414, "height": 896},   # iPhone 11
        ],
        DeviceType.TABLET: [
            {"width": 820, "height": 1180},  # iPad Air
            {"width": 768, "height": 1024},  # iPad
            {"width": 800, "height": 1280},  # Android tablet
        ],
    }
    
    def __init__(
        self,
        device_types: Optional[List[DeviceType]] = None,
        browser_types: Optional[List[BrowserType]] = None
    ):
        """
        Initialize the user agent rotator.
        
        Args:
            device_types: List of device types to include
            browser_types: List of browser types to include
        """
        self.device_types = device_types or [DeviceType.DESKTOP]
        self.browser_types = browser_types or [BrowserType.CHROME, BrowserType.FIREFOX]
        self._build_user_agent_pool()
        self._current_index = 0
    
    def _build_user_agent_pool(self):
        """Build the pool of available user agents based on configuration."""
        self.user_agents: List[UserAgentInfo] = []
        
        for device_type in self.device_types:
            for browser_type in self.browser_types:
                agents = self._get_agents_for_type(device_type, browser_type)
                for ua in agents:
                    self.user_agents.append(UserAgentInfo(
                        user_agent=ua,
                        device_type=device_type,
                        browser_type=browser_type,
                        platform=self._detect_platform(ua),
                        viewport=random.choice(self.VIEWPORTS[device_type])
                    ))
        
        # Shuffle for randomness
        random.shuffle(self.user_agents)
        logger.info(f"Built user agent pool with {len(self.user_agents)} agents")
    
    def _get_agents_for_type(
        self, 
        device_type: DeviceType, 
        browser_type: BrowserType
    ) -> List[str]:
        """Get user agents for specific device and browser type."""
        if device_type == DeviceType.DESKTOP:
            if browser_type == BrowserType.CHROME:
                return self.CHROME_DESKTOP
            elif browser_type == BrowserType.FIREFOX:
                return self.FIREFOX_DESKTOP
            elif browser_type == BrowserType.SAFARI:
                return self.SAFARI_DESKTOP
            elif browser_type == BrowserType.EDGE:
                return self.EDGE_DESKTOP
        elif device_type == DeviceType.MOBILE:
            if browser_type == BrowserType.CHROME:
                return self.CHROME_MOBILE
            elif browser_type == BrowserType.SAFARI:
                return self.SAFARI_MOBILE
        return []
    
    def _detect_platform(self, user_agent: str) -> str:
        """Detect platform from user agent string."""
        ua_lower = user_agent.lower()
        if "windows" in ua_lower:
            return "Windows"
        elif "macintosh" in ua_lower or "mac os" in ua_lower:
            return "macOS"
        elif "iphone" in ua_lower:
            return "iOS"
        elif "ipad" in ua_lower:
            return "iPadOS"
        elif "android" in ua_lower:
            return "Android"
        elif "linux" in ua_lower:
            return "Linux"
        return "Unknown"
    
    def get_random(self) -> UserAgentInfo:
        """Get a random user agent from the pool."""
        return random.choice(self.user_agents)
    
    def get_next(self) -> UserAgentInfo:
        """Get the next user agent in rotation."""
        ua = self.user_agents[self._current_index]
        self._current_index = (self._current_index + 1) % len(self.user_agents)
        return ua
    
    def get_for_domain(self, domain: str) -> UserAgentInfo:
        """
        Get a consistent user agent for a specific domain.
        Uses domain hash to ensure same UA is used for same domain.
        """
        domain_hash = hash(domain)
        index = abs(domain_hash) % len(self.user_agents)
        return self.user_agents[index]
    
    def get_headers(self, user_agent_info: Optional[UserAgentInfo] = None) -> Dict[str, str]:
        """
        Get complete HTTP headers for the user agent.
        
        Args:
            user_agent_info: Specific user agent to use, or random if None
        
        Returns:
            Dictionary of HTTP headers
        """
        if user_agent_info is None:
            user_agent_info = self.get_random()
        
        headers = {
            "User-Agent": user_agent_info.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9,en-US;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        
        # Add browser-specific headers
        if user_agent_info.browser_type == BrowserType.CHROME:
            headers["Sec-CH-UA"] = '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"'
            headers["Sec-CH-UA-Mobile"] = "?0" if user_agent_info.device_type == DeviceType.DESKTOP else "?1"
            headers["Sec-CH-UA-Platform"] = f'"{user_agent_info.platform}"'
        
        return headers


# Singleton instance for easy access
_default_rotator: Optional[UserAgentRotator] = None


def get_user_agent_rotator() -> UserAgentRotator:
    """Get the default user agent rotator instance."""
    global _default_rotator
    if _default_rotator is None:
        _default_rotator = UserAgentRotator()
    return _default_rotator