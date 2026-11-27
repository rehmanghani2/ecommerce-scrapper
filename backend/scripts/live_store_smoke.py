"""
Opt-in, bounded Playwright smoke checks for the four initial UK storefronts.

This script does not solve or bypass CAPTCHAs, authentication, queues, or access controls.
It checks robots.txt, stays on the configured storefront host, limits navigation count,
and emits a JSON report suitable for selector tuning.
Run from backend/: python scripts/live_store_smoke.py --output artifacts/store-smoke.json
"""
from __future__ import annotations

import argparse
import asyncio
import ipaddress
from functools import lru_cache
import json
import re
import socket
import time
import urllib.error
import urllib.robotparser
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from app.core.product_extractor import ProductExtractor
from app.scrapers.site_adapters import SITE_ADAPTERS, SiteAdapter


USER_AGENT = "EcommerceScraperCompatibilityTest/1.0 (+respectful storefront smoke test)"
NAVIGATION_TIMEOUT_MS = 25_000
MAX_CATEGORY_PAGES = 1
MAX_PAGINATION_PAGES = 1
MAX_PRODUCT_PAGES = 1
MAX_NAVIGATIONS_PER_SITE = 1 + MAX_CATEGORY_PAGES + MAX_PAGINATION_PAGES + MAX_PRODUCT_PAGES
NAVIGATION_DELAY_SECONDS = 1.5
CHALLENGE_MARKERS = (
    "verify you are human",
    "checking your browser",
    "captcha",
    "access denied",
    "unusual traffic",
    "security challenge",
    "datadome",
    "perimeterx",
    "cloudflare",
)


def _normalise_host(host: str | None) -> str:
    host = (host or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


@lru_cache(maxsize=512)
def _host_is_public(host: str, port: int) -> bool:
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        return bool(addresses) and all(
            ipaddress.ip_address(item[4][0]).is_global for item in addresses
        )
    except (OSError, ValueError, TypeError, OverflowError):
        return False


def _is_public_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        if parsed.username or parsed.password:
            return False
        host = parsed.hostname.lower().rstrip(".")
        if host == "localhost" or host.endswith(".local"):
            return False
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        return _host_is_public(host, port)
    except (OSError, ValueError, TypeError, OverflowError):
        return False


def _same_storefront(url: str, adapter: SiteAdapter) -> bool:
    return _normalise_host(urlparse(url).hostname) in {
        _normalise_host(host) for host in adapter.hosts
    }


def _robots_allows(url: str, timeout: int = 10) -> tuple[bool, str]:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    request = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(512_000).decode("utf-8", errors="replace")
        parser.parse(body.splitlines())
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        return False, f"robots.txt could not be checked: {type(exc).__name__}"
    allowed = parser.can_fetch(USER_AGENT, url)
    return allowed, "allowed by robots.txt" if allowed else "disallowed by robots.txt"


def _is_challenge(title: str, text: str) -> bool:
    sample = f"{title}\n{text[:6000]}".lower()
    return any(marker in sample for marker in CHALLENGE_MARKERS)


def _absolute_same_host_links(values: list[str], base_url: str, adapter: SiteAdapter) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        candidate = urljoin(base_url, (value or "").strip())
        parsed = urlparse(candidate)
        canonical_key = parsed._replace(netloc=_normalise_host(parsed.hostname)).geturl()
        if (
            parsed.scheme not in {"http", "https"}
            or not _same_storefront(candidate, adapter)
            or canonical_key in seen
            or not _is_public_http_url(candidate)
        ):
            continue
        seen.add(canonical_key)
        result.append(candidate)
    return result


async def _inspect_site(adapter: SiteAdapter, browser) -> dict[str, Any]:
    base_url = f"https://{adapter.hosts[0]}/"
    report: dict[str, Any] = {
        "site": adapter.key,
        "name": adapter.name,
        "base_url": base_url,
        "status": "started",
        "robots": None,
        "navigations": 0,
        "category_pages": [],
        "product_page": None,
        "errors": [],
    }

    if not _is_public_http_url(base_url):
        report.update(status="blocked", errors=["Target failed public-address validation"])
        return report

    allowed, robots_message = _robots_allows(base_url)
    report["robots"] = robots_message
    if not allowed:
        report.update(status="skipped_robots", errors=[robots_message])
        return report

    context = await browser.new_context(
        viewport={"width": 1440, "height": 1000},
        locale="en-GB",
        user_agent=USER_AGENT,
        ignore_https_errors=False,
    )

    async def guard_request(route):
        request_url = route.request.url
        parsed_request = urlparse(request_url)
        if parsed_request.scheme in {"http", "https"} and not _is_public_http_url(request_url):
            await route.abort("blockedbyclient")
            return
        if route.request.is_navigation_request():
            try:
                is_main_frame = route.request.frame.parent_frame is None
            except Exception:
                is_main_frame = False
            if is_main_frame:
                if not _same_storefront(request_url, adapter):
                    await route.abort("blockedbyclient")
                    return
                robots_ok, _ = _robots_allows(request_url)
                if not robots_ok:
                    await route.abort("blockedbyclient")
                    return
        await route.continue_()

    await context.route("**/*", guard_request)
    page = await context.new_page()
    page.set_default_navigation_timeout(NAVIGATION_TIMEOUT_MS)
    extractor = ProductExtractor()
    last_navigation = 0.0

    async def navigate(url: str) -> tuple[bool, str]:
        nonlocal last_navigation
        if report["navigations"] >= MAX_NAVIGATIONS_PER_SITE:
            return False, "navigation budget exhausted"
        if not _same_storefront(url, adapter) or not _is_public_http_url(url):
            return False, "URL failed same-host/public-address validation"
        robots_ok, robots_reason = _robots_allows(url)
        if not robots_ok:
            return False, robots_reason
        wait_for = NAVIGATION_DELAY_SECONDS - (time.monotonic() - last_navigation)
        if wait_for > 0:
            await asyncio.sleep(wait_for)
        try:
            response = await page.goto(url, wait_until="domcontentloaded")
            report["navigations"] += 1
            last_navigation = time.monotonic()
            await page.wait_for_timeout(700)
            if not _same_storefront(page.url, adapter):
                return False, "navigation redirected outside configured storefront host"
            if response and response.status >= 400:
                return False, f"HTTP {response.status}"
            return True, ""
        except Exception as exc:
            return False, f"{type(exc).__name__}: {str(exc)[:240]}"

    try:
        ok, error = await navigate(base_url)
        if not ok:
            report.update(status="failed", errors=[error])
            return report

        title = await page.title()
        body_text = await page.locator("body").inner_text(timeout=5000)
        if _is_challenge(title, body_text):
            report.update(status="challenge_detected", title=title)
            return report

        root_html = await page.content()
        root_products = extractor.extract(root_html, page.url)
        category_selector = ", ".join(adapter.category_selectors)
        category_hrefs = await page.locator("a[href]").evaluate_all(
            """(anchors, selectors) => anchors.filter(a => selectors.some(s => {
              try { return a.matches(s); } catch (_) { return false; }
            })).map(a => a.href)""",
            list(adapter.category_selectors),
        ) if adapter.category_selectors else []
        categories = _absolute_same_host_links(category_hrefs, page.url, adapter)
        report.update(
            status="inspected",
            title=title,
            root_product_cards=len(root_products),
            category_candidates=len(categories),
            category_selector=category_selector,
        )

        product_urls: list[str] = []
        for category_url in categories[:MAX_CATEGORY_PAGES]:
            ok, error = await navigate(category_url)
            category_result: dict[str, Any] = {
                "url": category_url,
                "loaded": ok,
                "error": error or None,
            }
            if ok:
                category_title = await page.title()
                category_text = await page.locator("body").inner_text(timeout=5000)
                if _is_challenge(category_title, category_text):
                    category_result["challenge_detected"] = True
                    report["category_pages"].append(category_result)
                    report["status"] = "challenge_detected"
                    break
                html = await page.content()
                products = extractor.extract(html, page.url)
                product_container = adapter.selector_config["product_container"]
                card_hrefs = await page.locator(f"{product_container} a[href]").evaluate_all(
                    "(anchors) => anchors.map(a => a.href).slice(0, 100)"
                )
                product_urls.extend(_absolute_same_host_links(card_hrefs, page.url, adapter))
                pagination_hrefs = await page.locator("a[href]").evaluate_all(
                    """(anchors, selectors) => anchors.filter(a => selectors.some(s => {
                      try { return a.matches(s); } catch (_) { return false; }
                    })).map(a => a.href)""",
                    list(adapter.pagination_selectors),
                ) if adapter.pagination_selectors else []
                pagination_urls = _absolute_same_host_links(pagination_hrefs, page.url, adapter)
                category_result.update(
                    title=category_title,
                    extracted_products=len(products),
                    product_link_candidates=len(card_hrefs),
                    pagination_candidates=len(pagination_urls),
                )
                if pagination_urls and report["navigations"] < MAX_NAVIGATIONS_PER_SITE - MAX_PRODUCT_PAGES:
                    next_url = pagination_urls[0]
                    next_ok, next_error = await navigate(next_url)
                    pagination_result = {
                        "url": next_url,
                        "loaded": next_ok,
                        "error": next_error or None,
                    }
                    if next_ok:
                        next_title = await page.title()
                        next_text = await page.locator("body").inner_text(timeout=5000)
                        if _is_challenge(next_title, next_text):
                            pagination_result["challenge_detected"] = True
                            report["status"] = "challenge_detected"
                        else:
                            next_products = extractor.extract(await page.content(), page.url)
                            pagination_result.update(
                                title=next_title,
                                extracted_products=len(next_products),
                            )
                    category_result["pagination_check"] = pagination_result
                    if pagination_result.get("loaded"):
                        next_card_hrefs = await page.locator(f"{product_container} a[href]").evaluate_all(
                            "(anchors) => anchors.map(a => a.href).slice(0, 100)"
                        )
                        product_urls.extend(_absolute_same_host_links(next_card_hrefs, page.url, adapter))
            report["category_pages"].append(category_result)

        if report["status"] == "challenge_detected":
            return report

        product_urls = list(dict.fromkeys(product_urls))
        if product_urls and report["navigations"] < MAX_NAVIGATIONS_PER_SITE:
            product_url = product_urls[0]
            ok, error = await navigate(product_url)
            product_result: dict[str, Any] = {"url": product_url, "loaded": ok, "error": error or None}
            if ok:
                product_title = await page.title()
                product_text = await page.locator("body").inner_text(timeout=5000)
                if _is_challenge(product_title, product_text):
                    product_result["challenge_detected"] = True
                    report["status"] = "challenge_detected"
                else:
                    products = extractor.extract(await page.content(), page.url)
                    product_result.update(
                        title=product_title,
                        extracted_records=len(products),
                        fields=sorted(products[0].keys()) if products else [],
                    )
            report["product_page"] = product_result

        report["status"] = report["status"] if report["status"] == "challenge_detected" else "completed"
        return report
    except Exception as exc:
        report["status"] = "failed"
        report["errors"].append(f"{type(exc).__name__}: {str(exc)[:300]}")
        return report
    finally:
        await context.close()


async def run_smoke_test(output: Path) -> list[dict[str, Any]]:
    from playwright.async_api import async_playwright

    results: list[dict[str, Any]] = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            for adapter in SITE_ADAPTERS:
                results.append(await _inspect_site(adapter, browser))
        finally:
            await browser.close()

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_agent": USER_AGENT,
        "limits": {
            "max_navigations_per_site": MAX_NAVIGATIONS_PER_SITE,
            "max_category_pages": MAX_CATEGORY_PAGES,
            "max_pagination_pages": MAX_PAGINATION_PAGES,
            "max_product_pages": MAX_PRODUCT_PAGES,
            "navigation_delay_seconds": NAVIGATION_DELAY_SECONDS,
        },
        "results": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run bounded live Playwright checks for supported UK stores.")
    parser.add_argument("--output", type=Path, default=Path("artifacts/store-smoke.json"))
    args = parser.parse_args()
    results = asyncio.run(run_smoke_test(args.output))
    for result in results:
        print(f"{result['site']}: {result['status']} ({result['navigations']} navigations)")
    print(f"Report written to {args.output}")
    return 1 if any(result["status"] in {"failed", "blocked"} for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
