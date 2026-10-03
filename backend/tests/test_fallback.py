import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.in_memory_pubsub import in_memory_pubsub
from app.core.playwright_scraper import PlaywrightScraper

@pytest.mark.asyncio
async def test_in_memory_pubsub():
    received = []
    
    async def callback(msg):
        received.append(msg)
        
    await in_memory_pubsub.subscribe("test_channel", callback)
    await in_memory_pubsub.publish("test_channel", {"hello": "world"})
    await asyncio.sleep(0.05)
    
    assert len(received) == 1
    assert received[0] == {"hello": "world"}
    
    await in_memory_pubsub.unsubscribe("test_channel", callback)
    await in_memory_pubsub.publish("test_channel", {"ignored": True})
    await asyncio.sleep(0.05)
    
    assert len(received) == 1

@pytest.mark.asyncio
async def test_playwright_scraper_fallback():
    # Mock HttpxScraper.run and sync_playwright launch failure
    with patch("playwright.sync_api.sync_playwright") as mock_playwright:
        # Make sync_playwright raise exception to simulate missing glib/dependencies
        mock_playwright.side_effect = Exception("chrome-headless-shell: error while loading shared libraries: libglib-2.0.so.0")
        
        # Instantiate PlaywrightScraper
        scraper = PlaywrightScraper(
            job_id=999,
            start_url="https://books.toscrape.com",
            max_pages=2,
            max_products=5,
        )
        
        # Mock HttpxScraper run to verify fallback execution
        with patch("app.core.httpx_scraper.HttpxScraper.run", new_callable=AsyncMock) as mock_httpx_run:
            await scraper.run()
            
            # Verify that HttpxScraper.run was indeed called due to fallback
            mock_httpx_run.assert_called_once()
