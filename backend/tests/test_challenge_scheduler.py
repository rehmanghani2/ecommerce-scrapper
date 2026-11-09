import asyncio
from types import SimpleNamespace

import pytest

from app.core.crawl_scheduler import CrawlScheduler
from app.core.url_frontier import URLFrontier


class FakeFetcher:
    def __init__(self):
        self.fetched = []

    async def fetch(self, url):
        self.fetched.append(url)
        return SimpleNamespace(
            success=False,
            html=None,
            challenge={
                "detected": True,
                "provider": "cloudflare",
                "confidence": 0.98,
                "signals": ["provider_signature:cloudflare", "challenge_text:just a moment"],
                "url": url,
                "http_status": 403,
            },
        )


class FakeExtractor:
    def extract_links(self, html, url):
        return []


class FakeProductExtractor:
    def extract(self, html, url):
        return []


@pytest.mark.asyncio
async def test_scheduler_stops_dispatching_after_access_challenge():
    frontier = URLFrontier("https://shop.example/")
    await frontier.add_url("https://shop.example/category", depth=1)

    fetcher = FakeFetcher()
    challenge_events = []

    async def on_challenge(url, challenge):
        challenge_events.append((url, challenge))

    scheduler = CrawlScheduler(
        frontier=frontier,
        fetcher=fetcher,
        extractor=FakeExtractor(),
        product_extractor=FakeProductExtractor(),
        on_challenge=on_challenge,
        max_concurrency=1,
        poll_interval=0.01,
    )

    await scheduler.run()

    assert scheduler.challenge_detected is True
    assert len(fetcher.fetched) == 1
    assert len(challenge_events) == 1
    assert challenge_events[0][1]["provider"] == "cloudflare"
