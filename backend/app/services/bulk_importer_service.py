"""
Bulk URL and File Importer Service.
Parses CSV, TSV, TXT files, and raw URL lists with column auto-mapping.
"""

import csv
import io
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

# Header aliases for URL columns
URL_COLUMN_ALIASES = [
    "url", "product_url", "link", "product_link", "web_url",
    "item_url", "page_url", "producturl", "productlink", "href"
]

NAME_COLUMN_ALIASES = [
    "name", "product_name", "title", "product_title", "item_name"
]

PRICE_COLUMN_ALIASES = [
    "price", "regular_price", "sale_price", "amount", "cost"
]

SKU_COLUMN_ALIASES = [
    "sku", "product_sku", "item_number", "id", "product_id"
]


class BulkImporterService:
    """Service to parse, validate, and extract URLs from uploaded files or raw text."""

    @staticmethod
    def is_valid_http_url(url: str) -> bool:
        """Validate if a string is a well-formed HTTP/HTTPS URL."""
        if not url or not isinstance(url, str):
            return False
        clean = url.strip()
        if not (clean.startswith("http://") or clean.startswith("https://")):
            return False
        try:
            parsed = urlparse(clean)
            return bool(parsed.netloc and "." in parsed.netloc)
        except Exception:
            return False

    def parse_csv_or_tsv(self, content_str: str) -> Dict[str, Any]:
        """
        Parse CSV or TSV string, detect header row and URL column,
        and return extracted URL items along with any pre-populated metadata.
        """
        # Detect delimiter (comma, tab, semicolon, pipe)
        first_few_lines = "\n".join(content_str.splitlines()[:5])
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(first_few_lines, delimiters=",\t;|")
            delimiter = dialect.delimiter
        except Exception:
            delimiter = "," if "\t" not in first_few_lines else "\t"

        reader = csv.reader(io.StringIO(content_str), delimiter=delimiter)
        rows = [row for row in reader if row and any(cell.strip() for cell in row)]

        if not rows:
            return {"success": False, "error": "CSV file is empty", "items": [], "urls": []}

        header = [c.strip().lower() for c in rows[0]]
        has_header = False
        url_idx = -1
        name_idx = -1
        price_idx = -1
        sku_idx = -1

        # Check if first row is a header
        for idx, col in enumerate(header):
            clean_col = col.replace(" ", "_").replace("-", "_")
            if any(alias in clean_col for alias in URL_COLUMN_ALIASES):
                url_idx = idx
                has_header = True
            elif any(alias in clean_col for alias in NAME_COLUMN_ALIASES):
                name_idx = idx
                has_header = True
            elif any(alias in clean_col for alias in PRICE_COLUMN_ALIASES):
                price_idx = idx
                has_header = True
            elif any(alias in clean_col for alias in SKU_COLUMN_ALIASES):
                sku_idx = idx
                has_header = True

        data_rows = rows[1:] if has_header else rows

        # If no explicit header matched a URL alias, find column where first data rows are valid URLs
        if url_idx == -1:
            for col_idx in range(len(data_rows[0])):
                sample_cell = data_rows[0][col_idx].strip()
                if self.is_valid_http_url(sample_cell):
                    url_idx = col_idx
                    break

        if url_idx == -1:
            # Fallback: scan all cells for HTTP URLs
            discovered = self.parse_raw_text(content_str)
            return discovered

        items: List[Dict[str, Any]] = []
        urls_set = set()

        for r in data_rows:
            if len(r) <= url_idx:
                continue
            raw_url = r[url_idx].strip()
            if self.is_valid_http_url(raw_url) and raw_url not in urls_set:
                urls_set.add(raw_url)
                item: Dict[str, Any] = {"url": raw_url}
                if name_idx >= 0 and len(r) > name_idx and r[name_idx].strip():
                    item["name"] = r[name_idx].strip()
                if price_idx >= 0 and len(r) > price_idx and r[price_idx].strip():
                    item["price"] = r[price_idx].strip()
                if sku_idx >= 0 and len(r) > sku_idx and r[sku_idx].strip():
                    item["sku"] = r[sku_idx].strip()
                items.append(item)

        return {
            "success": True,
            "delimiter": delimiter,
            "has_header": has_header,
            "total_rows": len(data_rows),
            "valid_urls_count": len(items),
            "urls": [it["url"] for it in items],
            "items": items,
        }

    def parse_raw_text(self, text: str) -> Dict[str, Any]:
        """Extract all valid HTTP/HTTPS URLs from raw text or newline-delimited lists."""
        url_pattern = re.compile(r'https?://[^\s<>"\',;]+')
        raw_matches = url_pattern.findall(text)

        cleaned_urls = []
        seen = set()
        for m in raw_matches:
            # Strip trailing punctuation
            u = m.rstrip(".,;)\"'")
            if self.is_valid_http_url(u) and u not in seen:
                seen.add(u)
                cleaned_urls.append(u)

        return {
            "success": True,
            "total_found": len(cleaned_urls),
            "urls": cleaned_urls,
            "items": [{"url": u} for u in cleaned_urls],
        }


bulk_importer_service = BulkImporterService()
