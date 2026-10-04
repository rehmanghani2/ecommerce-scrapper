"""
Visual Selector Picker Service.
Fetches, sanitizes, rewrites assets, and injects interactive inspection scripts
to enable real-time point-and-click CSS selector extraction in the UI.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class VisualPickerService:
    """Service to render web pages in an interactive sandbox for selector picking."""

    async def render_page_for_picker(self, url: str) -> str:
        """
        Fetch HTML from URL, rewrite relative resources to absolute,
        neutralize navigation/frame-busters, and inject the interactive selector picker overlay.
        """
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=False) as client:
                response = await client.get(url, headers=headers)
                html = response.text
        except Exception as e:
            logger.error(f"Failed to fetch {url} for visual picker: {e}")
            return f"""
            <html>
                <body style="font-family: sans-serif; padding: 40px; text-align: center; color: #ef4444;">
                    <h2>Unable to load webpage</h2>
                    <p>Failed to retrieve content from: <code>{url}</code></p>
                    <p><small>{str(e)}</small></p>
                </body>
            </html>
            """

        # Parse HTML
        soup = BeautifulSoup(html, "html.parser")

        # 1. Ensure or inject <base href="{url}">
        head = soup.find("head")
        if not head:
            head = soup.new_tag("head")
            if soup.html:
                soup.html.insert(0, head)
            else:
                soup.insert(0, head)

        base_tag = head.find("base")
        if not base_tag:
            base_tag = soup.new_tag("base", href=url)
            head.insert(0, base_tag)
        else:
            base_tag["href"] = url

        # 2. Rewrite resource URLs to absolute
        for tag in soup.find_all(["img", "script", "source", "iframe"]):
            if tag.get("src"):
                tag["src"] = urljoin(url, tag["src"])
            if tag.get("srcset"):
                # Handle srcset rewrite
                tag["srcset"] = self._rewrite_srcset(tag["srcset"], url)

        for tag in soup.find_all("link", rel="stylesheet"):
            if tag.get("href"):
                tag["href"] = urljoin(url, tag["href"])

        # 3. Neutralize navigation and frame-busters
        for s in soup.find_all("script"):
            script_text = s.string or ""
            # Strip scripts that attempt window redirection or busting iframes
            if any(term in script_text for term in ["top.location", "window.top", "window.location.replace", "location.href ="]):
                s.decompose()

        # 4. Inject Picker CSS and Inspector JS
        picker_code = f"""
        <style id="visual-picker-styles">
            .picker-highlight-hover {{
                outline: 2px dashed #3b82f6 !important;
                outline-offset: 1px !important;
                background-color: rgba(59, 130, 246, 0.15) !important;
                cursor: crosshair !important;
            }}
            .picker-highlight-selected {{
                outline: 2px solid #10b981 !important;
                outline-offset: 1px !important;
                background-color: rgba(16, 185, 129, 0.20) !important;
            }}
            #picker-badge {{
                position: fixed;
                z-index: 2147483647;
                background: #0f172a;
                color: #f8fafc;
                font-family: system-ui, -apple-system, sans-serif;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 8px;
                border-radius: 4px;
                pointer-events: none;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
                display: none;
                white-space: nowrap;
            }}
        </style>
        <div id="picker-badge"></div>
        <script id="visual-picker-script">
            (function() {{
                function getOptimalSelector(el) {{
                    if (!el || el.nodeType !== 1) return '';

                    // 1. Stable ID
                    if (el.id && !/\\d{{4,}}/.test(el.id) && !el.id.includes(':')) {{
                        return '#' + CSS.escape(el.id);
                    }}

                    // 2. Data attributes
                    for (const attr of ['data-testid', 'data-qa', 'data-product', 'data-hook', 'data-item']) {{
                        if (el.hasAttribute(attr)) {{
                            return '[' + attr + '="' + el.getAttribute(attr) + '"]';
                        }}
                    }}

                    const tag = el.tagName.toLowerCase();

                    // 3. Meaningful classes
                    const classes = Array.from(el.classList).filter(c => 
                        !c.startsWith('picker-') && 
                        !/^[a-z0-9]{{5,}}$/i.test(c) && 
                        !c.includes(':')
                    );

                    const keyClasses = classes.filter(c => 
                        /(product|title|name|price|item|card|img|image|money|amount|thumb|link|grid)/i.test(c)
                    );

                    if (keyClasses.length > 0) {{
                        const sel = tag + '.' + keyClasses.map(c => CSS.escape(c)).join('.');
                        if (document.querySelectorAll(sel).length < 50) {{
                            return sel;
                        }}
                    }}

                    if (classes.length > 0) {{
                        const sel = tag + '.' + classes.slice(0, 2).map(c => CSS.escape(c)).join('.');
                        if (document.querySelectorAll(sel).length < 50) {{
                            return sel;
                        }}
                    }}

                    // 4. Parent contextual hierarchy
                    let parent = el.parentElement;
                    if (parent && parent.tagName.toLowerCase() !== 'body') {{
                        const parentSel = getOptimalSelector(parent);
                        if (parentSel && !parentSel.includes(tag)) {{
                            return parentSel + ' ' + tag;
                        }}
                    }}

                    return tag;
                }}

                let hoveredEl = null;
                const badge = document.getElementById('picker-badge');

                // Intercept clicks
                document.addEventListener('click', function(e) {{
                    e.preventDefault();
                    e.stopPropagation();

                    const target = e.target.closest('*');
                    if (!target || target.id === 'picker-badge') return;

                    const selector = getOptimalSelector(target);
                    const matches = document.querySelectorAll(selector).length;

                    window.parent.postMessage({{
                        type: 'PICKER_ELEMENT_SELECTED',
                        selector: selector,
                        tagName: target.tagName.toLowerCase(),
                        text: (target.innerText || target.textContent || '').trim().slice(0, 150),
                        src: target.src || target.getAttribute('src') || (target.querySelector('img')?.src) || '',
                        href: target.href || target.getAttribute('href') || (target.closest('a')?.href) || '',
                        matchCount: matches
                    }}, '*');
                }}, true);

                // Hover highlighting
                document.addEventListener('mousemove', function(e) {{
                    const target = e.target;
                    if (!target || target.id === 'picker-badge' || target === hoveredEl) return;

                    if (hoveredEl) {{
                        hoveredEl.classList.remove('picker-highlight-hover');
                    }}

                    hoveredEl = target;
                    hoveredEl.classList.add('picker-highlight-hover');

                    const sel = getOptimalSelector(target);
                    badge.style.display = 'block';
                    badge.style.left = (e.clientX + 14) + 'px';
                    badge.style.top = (e.clientY + 14) + 'px';
                    badge.textContent = target.tagName.toLowerCase() + ' • ' + sel;
                }}, true);

                document.addEventListener('mouseleave', function() {{
                    if (hoveredEl) hoveredEl.classList.remove('picker-highlight-hover');
                    badge.style.display = 'none';
                }});

                // Listen for messages from parent container
                window.addEventListener('message', function(event) {{
                    if (!event.data) return;
                    if (event.data.type === 'HIGHLIGHT_QUERY') {{
                        document.querySelectorAll('.picker-highlight-selected').forEach(el => {{
                            el.classList.remove('picker-highlight-selected');
                        }});

                        const selector = event.data.selector;
                        if (!selector) return;

                        try {{
                            const matched = document.querySelectorAll(selector);
                            matched.forEach(el => el.classList.add('picker-highlight-selected'));

                            window.parent.postMessage({{
                                type: 'PICKER_QUERY_COUNT',
                                selector: selector,
                                count: matched.length
                            }}, '*');
                        }} catch (err) {{
                            // Invalid selector ignored
                        }}
                    }} else if (event.data.type === 'CLEAR_HIGHLIGHTS') {{
                        document.querySelectorAll('.picker-highlight-selected, .picker-highlight-hover').forEach(el => {{
                            el.classList.remove('picker-highlight-selected');
                            el.classList.remove('picker-highlight-hover');
                        }});
                    }}
                }});
            }})();
        </script>
        """

        if soup.body:
            soup.body.append(BeautifulSoup(picker_code, "html.parser"))
        else:
            soup.append(BeautifulSoup(picker_code, "html.parser"))

        return str(soup)

    @staticmethod
    def _rewrite_srcset(srcset: str, base_url: str) -> str:
        """Rewrite relative URLs inside a srcset string."""
        parts = srcset.split(",")
        rewritten = []
        for p in parts:
            p = p.strip()
            if not p:
                continue
            tokens = p.split(" ")
            tokens[0] = urljoin(base_url, tokens[0])
            rewritten.append(" ".join(tokens))
        return ", ".join(rewritten)

    async def test_custom_selectors(
        self,
        url: str,
        selectors: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Evaluate selectors on a live page and return element counts,
        samples, and structured product preview rows.
        """
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=False) as client:
                res = await client.get(url, headers=headers)
                html = res.text
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to fetch {url}: {str(e)}",
                "matched_elements": {},
                "preview_products": [],
            }

        soup = BeautifulSoup(html, "html.parser")
        matched_elements: Dict[str, Any] = {}

        for field_name, selector in selectors.items():
            if not selector:
                continue

            try:
                # Support ::attr(...) syntax
                css_part = selector
                attr_name = None
                if "::attr(" in selector:
                    css_part, attr_name = selector.split("::attr(")
                    attr_name = attr_name.rstrip(")")

                elements = soup.select(css_part) if css_part else [soup]
                samples = []
                for el in elements[:5]:
                    if attr_name:
                        val = el.get(attr_name, "")
                    elif el.name == "img":
                        val = el.get("src") or el.get("data-src") or ""
                    elif el.name == "a":
                        val = el.get("href") or el.get_text(strip=True)
                    else:
                        val = el.get_text(strip=True)

                    if val:
                        samples.append(str(val))

                matched_elements[field_name] = {
                    "count": len(elements),
                    "valid": True,
                    "samples": samples,
                }
            except Exception as e:
                matched_elements[field_name] = {
                    "count": 0,
                    "valid": False,
                    "error": str(e),
                    "samples": [],
                }

        # Generate structured product preview rows if container or items exist
        preview_products: List[Dict[str, Any]] = []
        container_sel = selectors.get("product_card") or selectors.get("product_container")

        if container_sel:
            try:
                containers = soup.select(container_sel)
                for c in containers[:10]:
                    prod = {}
                    # Name
                    name_sel = selectors.get("product_name")
                    if name_sel:
                        n_el = c.select_one(name_sel)
                        prod["name"] = n_el.get_text(strip=True) if n_el else None
                    # Price
                    price_sel = selectors.get("product_price")
                    if price_sel:
                        p_el = c.select_one(price_sel)
                        prod["price"] = p_el.get_text(strip=True) if p_el else None
                    # Image
                    img_sel = selectors.get("product_image")
                    if img_sel:
                        i_el = c.select_one(img_sel)
                        if i_el:
                            src = i_el.get("src") or i_el.get("data-src")
                            prod["image_url"] = urljoin(url, src) if src else None
                    # Link
                    link_sel = selectors.get("product_link")
                    if link_sel:
                        l_el = c.select_one(link_sel)
                        if l_el:
                            href = l_el.get("href")
                            prod["url"] = urljoin(url, href) if href else None

                    if prod.get("name") or prod.get("price") or prod.get("image_url"):
                        preview_products.append(prod)
            except Exception:
                pass

        return {
            "success": True,
            "url": url,
            "matched_elements": matched_elements,
            "preview_products": preview_products,
        }


visual_picker_service = VisualPickerService()
