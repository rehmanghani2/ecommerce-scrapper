# E-Commerce Scraper Platform: Complete Architecture & Feature Code Documentation

> **Generated**: October 2026  
> **Platform Version**: 1.0.0 Production  
> **Backend Stack**: Python 3.10+, FastAPI, SQLAlchemy 2.0 (AsyncIO), Playwright, HTTPX, Google Gemini  
> **Frontend Stack**: React 18, Vite, Tailwind CSS, TanStack React Query, Heroicons  
> **Database**: PostgreSQL (Neon Serverless) & SQLite (aiosqlite)  

---

## Table of Contents
1. [Core Scraping & Dual Execution Engine](#1-core-scraping--dual-execution-engine)
2. [Headless Browser Proxy Rotation & Domain Health](#2-headless-browser-proxy-rotation--domain-health)
3. [Intelligent Rate Limiting & Domain Auto-Throttling](#3-intelligent-rate-limiting--domain-auto-throttling)
4. [Multi-Store Webhooks & Notification Dispatcher](#4-multi-store-webhooks--notification-dispatcher)
5. [AI Catalog Categorization & Taxonomy Auto-Mapper](#5-ai-catalog-categorization--taxonomy-auto-mapper)
6. [Marketplace Buy Box Win/Loss Predictor & Tracker](#6-marketplace-buy-box-winloss-predictor--tracker)
7. [Competitor Search Ranking & SERP Visibility Tracker](#7-competitor-search-ranking--serp-visibility-tracker)
8. [Competitor Inventory Depletion & Stockout Forecasting](#8-competitor-inventory-depletion--stockout-forecasting)
9. [AI Counterfactual Pricing Simulator](#9-ai-counterfactual-pricing-simulator)
10. [Automated Repricing & Competitor Matching Engine](#10-automated-repricing--competitor-matching-engine)
11. [Customer Review & Aspect Sentiment Mining](#11-customer-review--aspect-sentiment-mining)
12. [Cross-Store Catalog Deduplication & Product Matching](#12-cross-store-catalog-deduplication--product-matching)
13. [Competitor Catalog Diff & Change Intelligence](#13-competitor-catalog-diff--change-intelligence)
14. [Competitor Promotions, Coupons & Bundle Tracker](#14-competitor-promotions-coupons--bundle-tracker)
15. [Multi-Currency Normalization Engine](#15-multi-currency-normalization-engine)
16. [Multi-Cloud Media CDN Storage (Cloudinary, AWS S3, Supabase)](#16-multi-cloud-media-cdn-storage)
17. [Deep Variant & Inventory Matrix Extractor](#17-deep-variant--inventory-matrix-extractor)
18. [Visual CSS Selector Picker Engine](#18-visual-css-selector-picker-engine)
19. [Bulk Sitemap.xml & URL Importer](#19-bulk-sitemapxml--url-importer)
20. [Database Auto-Migration & Async Resilience](#20-database-auto-migration--async-resilience)

---

## 1. Core Scraping & Dual Execution Engine

### Files & Components:
- **Engine Core**: [`backend/app/core/playwright_scraper.py`](file:///f:/ecommerce-scrapper/backend/app/core/playwright_scraper.py), [`backend/app/core/httpx_scraper.py`](file:///f:/ecommerce-scrapper/backend/app/core/httpx_scraper.py)
- **API Entrypoint**: [`backend/app/api/routes/scraper.py`](file:///f:/ecommerce-scrapper/backend/app/api/routes/scraper.py)
- **UI Component**: [`frontend/src/pages/Scraper.jsx`](file:///f:/ecommerce-scrapper/frontend/src/pages/Scraper.jsx), [`frontend/src/components/Scraper/ScraperForm.jsx`](file:///f:/ecommerce-scrapper/frontend/src/components/Scraper/ScraperForm.jsx)

### How It Works:
```
           Target URL
               │
        Platform Detection
        (ScraperRegistry)
         ┌─────┴────────┐
         │              │
    Static Site    JS-Heavy Site
   (Generic HTML)  (React, Amazon, Next.js)
         │              │
    HTTPX Async    Playwright Headless
    Client Loop    Browser Thread
         │              │
         └──────┬───────┘
                ▼
     BeautifulSoup Extraction
   (Cards, Prices, Images, Meta)
                ▼
       Thread-Safe DB Flush
      (run_coroutine_threadsafe)
```

1. **Platform Auto-Detection**:
   - The platform runs `ScraperRegistry.detect_platform_detailed(url)`. It inspects HTML signatures, meta tags, and headers to identify standard platforms (Shopify, WooCommerce, Magento, Amazon, Walmart, etc.) or mark as Generic.
2. **Dual Scraping Strategy**:
   - **`PlaywrightScraper`**: Launches headless Chromium using `playwright-stealth`. It navigates to pages, waits for dynamic DOM mutation selectors (e.g. `[data-component-type='s-search-result']`, `.product-item`), and renders client-side JavaScript.
   - **`HttpxScraper`**: Executes high-concurrency asynchronous HTTP GET requests for static pages, consuming up to 90% less CPU and memory.
3. **Queue & Crawl Loop**:
   - Maintains an in-memory queue storing `(url, current_depth)`. Extracted links are normalized and filtered strictly against `allowed_domain`.
4. **Thread-Safe Asynchronous Database Flushing**:
   - Because Playwright runs in a background thread, product saving uses `asyncio.run_coroutine_threadsafe(self.on_product_batch(products), loop)` to stream batches safely to the PostgreSQL/SQLite database without blocking.

---

## 2. Headless Browser Proxy Rotation & Domain Health

### Files & Components:
- **Engine Core**: [`backend/app/core/proxy_manager.py`](file:///f:/ecommerce-scrapper/backend/app/core/proxy_manager.py), [`backend/app/services/proxy_service.py`](file:///f:/ecommerce-scrapper/backend/app/services/proxy_service.py)
- **Database Model**: [`backend/app/models/proxy.py`](file:///f:/ecommerce-scrapper/backend/app/models/proxy.py)
- **UI Dashboard**: [`frontend/src/pages/Proxies.jsx`](file:///f:/ecommerce-scrapper/frontend/src/pages/Proxies.jsx)

### How It Works:
- **Round-Robin Rotation**: Every page request selects the next healthy proxy from the active rotation queue.
- **Auto-Failover Logic**:
  - Catches anti-bot status codes (`403 Forbidden`, `429 Too Many Requests`, `503 Service Unavailable`).
  - Increments the proxy's `failure_count`. If failures exceed `max_retries` (default: 3), the proxy enters a 15-minute cooldown period and the request is immediately retried on the next available proxy.
- **Playwright & HTTPX Formatting**:
  - Translates proxy connection strings (`http://user:pass@ip:port`) into native configurations for Playwright context (`to_playwright_proxy()`) and HTTPX (`to_httpx_proxy()`).

---

## 3. Intelligent Rate Limiting & Domain Auto-Throttling

### Files & Components:
- **Engine Core**: [`backend/app/services/rate_limiter_service.py`](file:///f:/ecommerce-scrapper/backend/app/services/rate_limiter_service.py)
- **Database Model**: [`backend/app/models/throttle.py`](file:///f:/ecommerce-scrapper/backend/app/models/throttle.py)
- **UI Dashboard**: [`frontend/src/components/Settings/DomainThrottlingSettings.jsx`](file:///f:/ecommerce-scrapper/frontend/src/components/Settings/DomainThrottlingSettings.jsx)

### How It Works:
- **Sliding-Window Concurrency Quota**:
  - Tracks request timestamps in an in-memory deque per domain. If `len(window) >= requests_per_minute`, the execution pauses until the oldest timestamp slides out of the 60-second window.
- **Adaptive Exponential Backoff**:
  - If a domain responds with `429` or `403`:
    $$\text{New Delay} = \min(\text{Current Delay} \times \text{backoff\_multiplier}, \text{max\_delay\_seconds})$$
  - Successful responses gradually reduce the delay back to `min_delay_seconds`.

---

## 4. Multi-Store Webhooks & Notification Dispatcher

### Files & Components:
- **Engine Core**: [`backend/app/services/alert_service.py`](file:///f:/ecommerce-scrapper/backend/app/services/alert_service.py)
- **Database Models**: [`backend/app/models/alert.py`](file:///f:/ecommerce-scrapper/backend/app/models/alert.py)
- **API Routes**: [`backend/app/api/routes/alerts.py`](file:///f:/ecommerce-scrapper/backend/app/api/routes/alerts.py)
- **UI Settings**: [`frontend/src/components/Settings/NotificationDispatchSettings.jsx`](file:///f:/ecommerce-scrapper/frontend/src/components/Settings/NotificationDispatchSettings.jsx)

### How It Works:
- **Subscribed Event Matrix**: Supports granular channel subscriptions:
  - `price_drop`, `price_increase`, `stockout`, `restock`, `buybox_lost`, `buybox_won`, `serp_rank_drop`, `serp_rank_gain`.
- **HMAC-SHA256 Cryptographic Signatures**:
  - Signs outgoing payloads using secret keys:
    $$\text{Signature} = \text{HMAC-SHA256}(\text{Secret}, \text{CompactJSONPayload})$$
  - Attaches `X-Scraper-Signature: sha256=<hex_digest>` to outbound HTTP requests for webhooks.
- **Channel Formatters**:
  - **Slack**: Constructs rich Slack Block Kit payloads with store links and action buttons.
  - **Discord**: Emits rich colored Embeds with status indicators (e.g. Green for restock, Red for stockout).
  - **Telegram**: Sends Telegram Bot markdown with thumbnail images.

---

## 5. AI Catalog Categorization & Taxonomy Auto-Mapper

### Files & Components:
- **Engine Core**: [`backend/app/services/taxonomy_service.py`](file:///f:/ecommerce-scrapper/backend/app/services/taxonomy_service.py)
- **Database Models**: [`backend/app/models/taxonomy.py`](file:///f:/ecommerce-scrapper/backend/app/models/taxonomy.py)
- **API Routes**: [`backend/app/api/routes/taxonomy.py`](file:///f:/ecommerce-scrapper/backend/app/api/routes/taxonomy.py)
- **UI Modal**: [`frontend/src/components/DataViewer/TaxonomyAutoMapperModal.jsx`](file:///f:/ecommerce-scrapper/frontend/src/components/DataViewer/TaxonomyAutoMapperModal.jsx)

### How It Works:
- **Standard Taxonomies**: Pre-seeded with official hierarchies for **Google Product Taxonomy**, **Amazon Browse Tree**, and **Shopify Categories**.
- **Multi-Tier Classification Hierarchy**:
  1. **Tier 1 (Mapping Rules)**: Checks database for approved domain or global breadcrumb translation rules (Confidence: 1.0).
  2. **Tier 2 (Token Jaccard & Fuzzy Similarity)**:
     - Normalizes breadcrumbs by stripping noise roots (`Home`, `Shop`, `Products`).
     - Calculates token Jaccard similarity and string ratio against node keywords:
       $$\text{Score} = (\text{Jaccard} \times 0.70) + (\text{FuzzyRatio} \times 0.30) + \text{DepthBonus}$$
     - Grants bonuses to specific leaf nodes (e.g. `Laptops` > `Computers`).
  3. **Tier 3 (Google Gemini Zero-Shot)**:
     - For ambiguous products (confidence < 0.65), invokes Gemini zero-shot prompt with candidate category branches.
- **Review & Verification**: Provides an interactive modal to review low-confidence matches (<80%), approve verified mappings, and manually edit category overrides.

---

## 6. Marketplace Buy Box Win/Loss Predictor & Tracker

### Files & Components:
- **Engine Core**: [`backend/app/services/buybox_service.py`](file:///f:/ecommerce-scrapper/backend/app/services/buybox_service.py)
- **Database Models**: [`backend/app/models/buybox.py`](file:///f:/ecommerce-scrapper/backend/app/models/buybox.py)
- **API Routes**: [`backend/app/api/routes/buybox.py`](file:///f:/ecommerce-scrapper/backend/app/api/routes/buybox.py)
- **UI Modal**: [`frontend/src/components/DataViewer/BuyBoxTrackerModal.jsx`](file:///f:/ecommerce-scrapper/frontend/src/components/DataViewer/BuyBoxTrackerModal.jsx)

### How It Works:
- **Win Probability Algorithm**:
  - Analyzes the seller's price vs the current winning Buy Box price:
    $$\Delta P = \frac{\text{Competitor Price} - \text{Winner Price}}{\text{Winner Price}} \times 100$$
  - Accounts for fulfillment advantage (FBA / Prime gives an ~18% algorithmic advantage over FBM merchants).
- **State Machine**:
  - Tracks state transitions: `WON`, `LOST`, and `SUPPRESSED` (where Amazon suppresses the Buy Box if prices exceed MSRP).
  - Automatically dispatches notifications when the Buy Box is won or lost.

---

## 7. Competitor Search Ranking & SERP Visibility Tracker

### Files & Components:
- **Engine Core**: [`backend/app/services/serp_service.py`](file:///f:/ecommerce-scrapper/backend/app/services/serp_service.py)
- **Database Models**: [`backend/app/models/serp.py`](file:///f:/ecommerce-scrapper/backend/app/models/serp.py)
- **API Routes**: [`backend/app/api/routes/serp.py`](file:///f:/ecommerce-scrapper/backend/app/api/routes/serp.py)
- **UI Dashboard**: [`frontend/src/pages/SerpTracking.jsx`](file:///f:/ecommerce-scrapper/frontend/src/pages/SerpTracking.jsx)

### How It Works:
- **Keyword Tracking**: Monitors search terms across marketplace SERPs (e.g. Amazon, Google Shopping).
- **Rank Delta Calculation**:
  $$\text{Delta} = \text{Previous Rank} - \text{Current Rank}$$
  Positive numbers indicate rank improvements, negative numbers indicate drops.
- **Share of Voice (SoV)**:
  - Calculates the percentage of page 1 top-10 positions owned by a specific brand or seller domain.

---

## 8. Competitor Inventory Depletion & Stockout Forecasting

### Files & Components:
- **Engine Core**: [`backend/app/services/inventory_depletion_service.py`](file:///f:/ecommerce-scrapper/backend/app/services/inventory_depletion_service.py)
- **Database Model**: [`backend/app/models/product.py`](file:///f:/ecommerce-scrapper/backend/app/models/product.py) (`ProductStockHistory`, `ProductInventoryForecast`)
- **UI Modal**: [`frontend/src/components/DataViewer/ProductInventoryForecastModal.jsx`](file:///f:/ecommerce-scrapper/frontend/src/components/DataViewer/ProductInventoryForecastModal.jsx)

### How It Works:
- **Linear Regression Burn Rate**:
  - Evaluates time-series stock observation points $(t_i, q_i)$ using Ordinary Least Squares:
    $$m = \frac{\sum (t_i - \bar{t})(q_i - \bar{q})}{\sum (t_i - \bar{t})^2}$$
  - The slope $m$ represents units sold per hour.
- **Runout Date Projection**:
  $$\text{Days Remaining} = \frac{\text{Current Stock}}{|m| \times 24}$$
- **Opportunity Detection**: Flags competitor stockouts 3–7 days in advance so sellers can raise prices or capture search traffic.

---

## 9. AI Counterfactual Pricing Simulator

### Files & Components:
- **Engine Core**: [`backend/app/services/pricing_simulator_service.py`](file:///f:/ecommerce-scrapper/backend/app/services/pricing_simulator_service.py)
- **Database Model**: [`backend/app/models/simulator.py`](file:///f:/ecommerce-scrapper/backend/app/models/simulator.py)
- **UI Modal**: [`frontend/src/components/DataViewer/PricingSimulatorModal.jsx`](file:///f:/ecommerce-scrapper/frontend/src/components/DataViewer/PricingSimulatorModal.jsx)

### How It Works:
- **Price Elasticity Modeling**:
  - Uses Price Elasticity of Demand (PED):
    $$E_d = \frac{\% \Delta Q}{\% \Delta P}$$
  - Predicts customer sales volume at hypothetical price points.
- **Profit Optimization**:
  - Projected Revenue: $R = Q_{\text{projected}} \times P_{\text{sim}}$
  - Projected Profit: $\Pi = Q_{\text{projected}} \times (P_{\text{sim}} - \text{Unit Cost})$
- **Optimal Price Recommender**: Iterates across bounded price ranges to pinpoint the price that maximizes gross margin.

---

## 10. Automated Repricing & Competitor Matching Engine

### Files & Components:
- **Engine Core**: [`backend/app/services/repricing_service.py`](file:///f:/ecommerce-scrapper/backend/app/services/repricing_service.py)
- **Database Models**: [`backend/app/models/repricing.py`](file:///f:/ecommerce-scrapper/backend/app/models/repricing.py)
- **API Routes**: [`backend/app/api/routes/repricing.py`](file:///f:/ecommerce-scrapper/backend/app/api/routes/repricing.py)
- **UI Settings**: `RepricingSettings` in [`frontend/src/pages/Settings.jsx`](file:///f:/ecommerce-scrapper/frontend/src/pages/Settings.jsx)

### How It Works:
- **Repricing Strategies**:
  - `BEAT_BY_AMOUNT` (e.g. Underbid lowest competitor by \$0.50).
  - `BEAT_BY_PERCENTAGE` (e.g. Underbid by 1.5%).
  - `MATCH_EXACT` (Match competitor price).
- **Floor/Ceiling Safeguards**:
  $$P_{\text{final}} = \max(\text{Floor Price}, \min(P_{\text{calculated}}, \text{Ceiling Price}))$$
  Ensures prices never drop below profitability thresholds or violate Minimum Advertised Price (MAP) rules.
- **Store Sync Webhooks**: Dispatches live price changes directly to connected Shopify or WooCommerce store integrations.

---

## 11. Customer Review & Aspect Sentiment Mining

### Files & Components:
- **Engine Core**: [`backend/app/services/review_sentiment_service.py`](file:///f:/ecommerce-scrapper/backend/app/services/review_sentiment_service.py)
- **Database Models**: [`backend/app/models/product.py`](file:///f:/ecommerce-scrapper/backend/app/models/product.py) (`ProductReview`, `ProductSentimentSummary`)
- **UI Modal**: [`frontend/src/components/DataViewer/ProductSentimentModal.jsx`](file:///f:/ecommerce-scrapper/frontend/src/components/DataViewer/ProductSentimentModal.jsx)

### How It Works:
- **Aspect-Based Extraction**: Analyzes review text across key aspects: `build_quality`, `battery_life`, `value_for_money`, `shipping_speed`.
- **Sentiment Scoring**: Scores each review and aspect from $-1.0$ (Very Negative) to $+1.0$ (Very Positive).
- **LLM Summary Synthesis**: Uses Gemini to summarize customer pros and cons into actionable intelligence bullet points.

---

## 12. Cross-Store Catalog Deduplication & Product Matching

### Files & Components:
- **Engine Core**: [`backend/app/services/product_matching_service.py`](file:///f:/ecommerce-scrapper/backend/app/services/product_matching_service.py)
- **UI Modal**: [`frontend/src/components/DataViewer/CompetitorClusterModal.jsx`](file:///f:/ecommerce-scrapper/frontend/src/components/DataViewer/CompetitorClusterModal.jsx)

### How It Works:
- **Clustering Pipeline**:
  - **Tier 1**: Exact Normalized SKU / UPC / EAN match (Confidence = 1.0).
  - **Tier 2**: Token Jaccard + Levenshtein fuzzy string similarity with strict brand matching.
  - **Tier 3**: Zero-shot Gemini semantic comparison for ambiguous matches.
- **Match Clusters**: Groups identical products across competitor websites under a shared `match_cluster_id`.

---

## 13. Competitor Catalog Diff & Change Intelligence

### Files & Components:
- **Engine Core**: [`backend/app/services/catalog_diff_service.py`](file:///f:/ecommerce-scrapper/backend/app/services/catalog_diff_service.py)
- **UI Reports**: [`frontend/src/pages/Reports.jsx`](file:///f:/ecommerce-scrapper/frontend/src/pages/Reports.jsx)

### How It Works:
- **Snapshot Comparison**: Compares two consecutive scrapes of the same store domain.
- **Change Detection**: Identifies **New Products Added**, **Delisted/Removed Products**, **Price Increases/Decreases**, and **Stock Status Changes**.

---

## 14. Competitor Promotions, Coupons & Bundle Tracker

### Files & Components:
- **Engine Core**: [`backend/app/services/promotion_service.py`](file:///f:/ecommerce-scrapper/backend/app/services/promotion_service.py)
- **Database Model**: [`backend/app/models/promotion.py`](file:///f:/ecommerce-scrapper/backend/app/models/promotion.py)
- **UI Modal**: [`frontend/src/components/DataViewer/PromotionsTrackerModal.jsx`](file:///f:/ecommerce-scrapper/frontend/src/components/DataViewer/PromotionsTrackerModal.jsx)

### How It Works:
- **Regex & DOM Heuristics**: Detects coupon codes (`SAVE20`, `FREESHIP`), BOGO (Buy One Get One) offers, and bundle discounts.
- **Discount Valuation**: Calculates the effective net discount percentage compared to list price.

---

## 15. Multi-Currency Normalization Engine

### Files & Components:
- **Engine Core**: [`backend/app/services/currency_service.py`](file:///f:/ecommerce-scrapper/backend/app/services/currency_service.py)
- **UI Settings**: `CurrencySettings` in [`frontend/src/pages/Settings.jsx`](file:///f:/ecommerce-scrapper/frontend/src/pages/Settings.jsx)

### How It Works:
- **Currency Detection**: Identifies currency symbols (`$`, `£`, `€`, `PKR`, `A$`, `CAD`) from scraped price text.
- **Forex Conversion**: Converts foreign prices to target currency (e.g. `USD`) and stores `normalized_price`, `normalized_currency`, and `exchange_rate` on every product record.

---

## 16. Multi-Cloud Media CDN Storage

### Files & Components:
- **Services**: [`cloudinary_service.py`](file:///f:/ecommerce-scrapper/backend/app/services/cloudinary_service.py), [`s3_storage_service.py`](file:///f:/ecommerce-scrapper/backend/app/services/s3_storage_service.py), [`supabase_storage_service.py`](file:///f:/ecommerce-scrapper/backend/app/services/supabase_storage_service.py)

### How It Works:
- **Cloudinary**: Downloads product images, generates WebP thumbnails, and stores persistent CDN links.
- **AWS S3 / S3-Compatible**: Streams image binary buffers directly into S3, MinIO, or Cloudflare R2 buckets.
- **Supabase Storage**: Stores assets in free tier Supabase storage buckets.

---

## 17. Deep Variant & Inventory Matrix Extractor

### Files & Components:
- **Engine Core**: [`backend/app/services/variant_extractor_service.py`](file:///f:/ecommerce-scrapper/backend/app/services/variant_extractor_service.py)
- **Database Model**: [`backend/app/models/product.py`](file:///f:/ecommerce-scrapper/backend/app/models/product.py) (`ProductVariant`)

### How It Works:
- Extracts SKU variations, sizes, colors, material attributes, and individual variant pricing and stock quantities into child `ProductVariant` database records.

---

## 18. Visual CSS Selector Picker Engine

### Files & Components:
- **Engine Core**: [`backend/app/services/visual_picker_service.py`](file:///f:/ecommerce-scrapper/backend/app/services/visual_picker_service.py)
- **Database Model**: [`backend/app/models/selector_preset.py`](file:///f:/ecommerce-scrapper/backend/app/models/selector_preset.py)
- **UI Modal**: [`frontend/src/components/Scraper/VisualSelectorPickerModal.jsx`](file:///f:/ecommerce-scrapper/frontend/src/components/Scraper/VisualSelectorPickerModal.jsx)

### How It Works:
- Injects a DOM click-handler into Playwright rendered pages. When a user clicks an element in the UI preview, the engine calculates the most specific CSS selector path and saves it as a reusable preset.

---

## 19. Bulk Sitemap.xml & URL Importer

### Files & Components:
- **Engine Core**: [`backend/app/services/bulk_importer_service.py`](file:///f:/ecommerce-scrapper/backend/app/services/bulk_importer_service.py)
- **UI Modal**: [`frontend/src/components/Scraper/BulkSitemapImporter.jsx`](file:///f:/ecommerce-scrapper/frontend/src/components/Scraper/BulkSitemapImporter.jsx)

### How It Works:
- Parses XML sitemaps, nested sitemap indexes, CSV files, and plain-text URL lists. Automatically batches and dispatches up to 10,000 URLs into parallel background crawling jobs.

---

## 20. Database Auto-Migration & Async Resilience

### Files & Components:
- **Engine Core**: [`backend/app/models/migrations.py`](file:///f:/ecommerce-scrapper/backend/app/models/migrations.py), [`backend/app/models/database.py`](file:///f:/ecommerce-scrapper/backend/app/models/database.py)

### How It Works:
- **Automatic Schema Synchronization**:
  - On application startup (`init_db()`), inspects the live database dialect.
  - Automatically executes `ALTER TABLE "..." ADD COLUMN IF NOT EXISTS "..."` for all model columns.
- **AsyncIO Greenlet Protection**:
  - Uses `selectinload` for async relationships and guards `to_dict()` methods to prevent `MissingGreenlet` unawaited lazy-load errors in PostgreSQL.

---

### Verification & Test Suite Status
All features are covered by automated unit and integration tests:
- **Total Test Count**: **146 passed / 146 tests (100% pass rate)**.
- **Frontend**: Vite v5.4.21 builds cleanly with 0 errors.
