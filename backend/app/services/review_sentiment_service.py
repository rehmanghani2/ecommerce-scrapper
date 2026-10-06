"""
Customer Review & Competitor Sentiment Mining Service.
Analyzes competitor reviews using:
1. Fast rule-based star rating & lexicon sentiment scoring (offline / heuristic)
2. Google Gemini 2.5 Flash Zero-Shot Deep Sentiment & Weakness Theme Mining
3. Aggregation of competitor product flaws, vulnerabilities, and buyer pain points
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.config import settings
from app.models.product import Product, ProductReview, ProductSentimentSummary

logger = logging.getLogger(__name__)


class ReviewSentimentService:
    """Service to ingest, classify sentiment, and mine competitor product weaknesses."""

    POSITIVE_WORDS = {
        "great", "excellent", "love", "loved", "perfect", "amazing", "good", "best",
        "superb", "awesome", "fantastic", "durable", "sturdy", "quality", "fast",
        "smooth", "beautiful", "impressed", "worth", "highly", "recommend", "flawless"
    }

    NEGATIVE_WORDS = {
        "bad", "terrible", "awful", "horrible", "broke", "broken", "defective", "waste",
        "poor", "cheap", "flimsy", "slow", "useless", "disappointed", "disappointing",
        "worst", "hate", "scam", "cracked", "died", "refund", "returned", "junk", "regret"
    }

    COMMON_TOPIC_KEYWORDS = {
        "battery": "battery life",
        "charge": "battery life",
        "sound": "sound quality",
        "audio": "sound quality",
        "bass": "sound quality",
        "fit": "comfort & fit",
        "comfort": "comfort & fit",
        "ear": "comfort & fit",
        "size": "sizing",
        "screen": "display",
        "display": "display",
        "build": "build quality",
        "material": "build quality",
        "plastic": "build quality",
        "price": "pricing & value",
        "expensive": "pricing & value",
        "value": "pricing & value",
        "shipping": "shipping & packaging",
        "delivery": "shipping & packaging",
        "box": "shipping & packaging",
        "package": "shipping & packaging",
        "app": "software & connectivity",
        "bluetooth": "software & connectivity",
        "connection": "software & connectivity",
        "wifi": "software & connectivity",
    }

    def __init__(self):
        self.default_model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")

    def analyze_review_heuristic(self, content: str, rating: Optional[float] = None) -> Tuple[str, float, List[str]]:
        """
        Heuristic offline sentiment classification and topic tagger.
        Returns: (sentiment: str, sentiment_score: float, key_topics: List[str])
        """
        text = (content or "").lower()
        words = re.findall(r"\b\w+\b", text)

        pos_count = sum(1 for w in words if w in self.POSITIVE_WORDS)
        neg_count = sum(1 for w in words if w in self.NEGATIVE_WORDS)

        # Baseline score from words (-1.0 to 1.0)
        total_matched = pos_count + neg_count
        if total_matched > 0:
            score = (pos_count - neg_count) / total_matched
        else:
            score = 0.0

        # Adjust score with star rating if available
        if rating is not None:
            # Map 1-5 stars to -1.0 to +1.0
            rating_normalized = (rating - 3.0) / 2.0
            score = 0.5 * score + 0.5 * rating_normalized

        score = round(max(-1.0, min(1.0, score)), 2)

        if score >= 0.25:
            sentiment = "positive"
        elif score <= -0.25:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        # Topic tagging
        topics = set()
        for kw, topic_name in self.COMMON_TOPIC_KEYWORDS.items():
            if kw in words or kw in text:
                topics.add(topic_name)

        return sentiment, score, list(topics)

    async def analyze_with_ai(
        self,
        product_name: str,
        reviews: List[Dict[str, Any]],
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Use Google Gemini Zero-Shot sentiment and competitor weakness mining.
        """
        key = api_key or settings.GEMINI_API_KEY
        if not key:
            return {
                "success": False,
                "error": "Gemini API key is not configured",
            }

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.default_model}:generateContent?key={key}"

        reviews_snippet = "\n".join([
            f"Review #{idx+1} [Rating: {r.get('rating', 'N/A')}★, Title: {r.get('title', '')}]: {r.get('content', '')}"
            for idx, r in enumerate(reviews[:30])
        ])

        system_instruction = (
            "You are a Senior E-Commerce Market Intelligence and Consumer Sentiment Analyst. "
            "Analyze the provided customer reviews for a competitor product. "
            "Identify the product's market reception, recurring flaws/weaknesses, and buyer pain points. "
            "Return a strictly valid JSON object with the following schema:\n"
            "- positive_percentage (number, 0-100)\n"
            "- neutral_percentage (number, 0-100)\n"
            "- negative_percentage (number, 0-100)\n"
            "- key_strengths (array of strings, 3-5 top advantages praised by customers)\n"
            "- key_weaknesses (array of strings, 3-5 notable product flaws or competitor vulnerabilities)\n"
            "- buyer_pain_points (array of strings, 3-5 common frustrations or complaints)\n"
            "- summary_verdict (string, 2-3 sentence executive synthesis of competitor product health)\n"
            "- review_classifications (array of objects with 'index' (int), 'sentiment' ('positive'|'neutral'|'negative'), 'key_topics' (array of strings))"
        )

        prompt = f"Product: {product_name}\n\nCustomer Reviews:\n{reviews_snippet}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": system_instruction},
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(endpoint, json=payload)
                if res.status_code != 200:
                    logger.error(f"Gemini Sentiment API returned HTTP {res.status_code}: {res.text[:300]}")
                    return {"success": False, "error": f"AI error HTTP {res.status_code}"}

                data = res.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return {"success": False, "error": "No response returned by AI"}

                raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                parsed = json.loads(raw_text)
                parsed["success"] = True
                return parsed
        except Exception as e:
            logger.error(f"Error in Gemini sentiment analysis: {e}")
            return {"success": False, "error": str(e)}

    async def ingest_reviews(
        self,
        db: AsyncSession,
        product_id: int,
        reviews_data: List[Dict[str, Any]],
        run_ai: bool = False,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Store batch of product reviews and calculate initial heuristic sentiment.
        Optionally triggers deep AI sentiment mining.
        """
        product = await db.get(Product, product_id)
        if not product:
            return {"success": False, "error": "Product not found", "count": 0}

        saved_reviews = []
        for r in reviews_data:
            content = r.get("content") or r.get("text") or ""
            if not content.strip():
                continue

            rating = float(r.get("rating")) if r.get("rating") is not None else None
            sentiment, score, topics = self.analyze_review_heuristic(content, rating)

            review = ProductReview(
                product_id=product.id,
                author=r.get("author") or "Anonymous",
                rating=rating,
                title=r.get("title"),
                content=content.strip(),
                verified_purchase=bool(r.get("verified_purchase", False)),
                helpful_votes=int(r.get("helpful_votes", 0)),
                sentiment=sentiment,
                sentiment_score=score,
                key_topics=topics,
            )
            db.add(review)
            saved_reviews.append(review)

        await db.flush()

        # Update or create summary
        await self.recalculate_sentiment_summary(db, product_id, run_ai=run_ai, api_key=api_key)
        await db.commit()

        return {
            "success": True,
            "message": f"Successfully ingested {len(saved_reviews)} reviews",
            "reviews_added": len(saved_reviews),
        }

    async def recalculate_sentiment_summary(
        self,
        db: AsyncSession,
        product_id: int,
        run_ai: bool = False,
        api_key: Optional[str] = None
    ) -> Optional[ProductSentimentSummary]:
        """
        Recalculate sentiment metrics and competitor weakness themes for a product.
        """
        product = await db.get(Product, product_id)
        if not product:
            return None

        # Fetch reviews
        stmt = select(ProductReview).where(ProductReview.product_id == product_id)
        res = await db.execute(stmt)
        reviews = res.scalars().all()

        if not reviews:
            return None

        total = len(reviews)
        ratings = [r.rating for r in reviews if r.rating is not None]
        avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None

        pos = sum(1 for r in reviews if r.sentiment == "positive")
        neu = sum(1 for r in reviews if r.sentiment == "neutral")
        neg = sum(1 for r in reviews if r.sentiment == "negative")

        pos_pct = round((pos / total) * 100, 1)
        neu_pct = round((neu / total) * 100, 1)
        neg_pct = round((neg / total) * 100, 1)

        # Check existing summary
        sum_stmt = select(ProductSentimentSummary).where(ProductSentimentSummary.product_id == product_id)
        sum_res = await db.execute(sum_stmt)
        summary = sum_res.scalar_one_or_none()

        if not summary:
            summary = ProductSentimentSummary(product_id=product_id)
            db.add(summary)

        summary.total_reviews_analyzed = total
        summary.average_rating = avg_rating
        summary.positive_percentage = pos_pct
        summary.neutral_percentage = neu_pct
        summary.negative_percentage = neg_pct
        summary.last_analyzed_at = datetime.now(timezone.utc)

        # Rule-based default weaknesses from negative reviews
        default_weaknesses = []
        default_pain_points = []
        default_strengths = []

        for r in reviews:
            if r.sentiment == "negative":
                for top in (r.key_topics or []):
                    if top not in default_weaknesses and len(default_weaknesses) < 5:
                        default_weaknesses.append(f"Criticism regarding {top}")
            elif r.sentiment == "positive":
                for top in (r.key_topics or []):
                    if top not in default_strengths and len(default_strengths) < 5:
                        default_strengths.append(f"Praise for {top}")

        summary.key_strengths = default_strengths or ["General customer satisfaction"]
        summary.key_weaknesses = default_weaknesses or ["No major recurring flaws detected"]
        summary.buyer_pain_points = default_pain_points or ["Occasional buyer delivery and fit questions"]
        summary.summary_verdict = (
            f"Product maintains {pos_pct}% positive customer reception with an average {avg_rating or 0}★ rating across {total} reviews."
        )

        # Optional Deep AI Analysis
        if run_ai:
            raw_review_dicts = [{"rating": r.rating, "title": r.title, "content": r.content} for r in reviews]
            ai_data = await self.analyze_with_ai(product.name, raw_review_dicts, api_key=api_key)
            if ai_data.get("success"):
                summary.positive_percentage = float(ai_data.get("positive_percentage", pos_pct))
                summary.neutral_percentage = float(ai_data.get("neutral_percentage", neu_pct))
                summary.negative_percentage = float(ai_data.get("negative_percentage", neg_pct))
                summary.key_strengths = ai_data.get("key_strengths") or summary.key_strengths
                summary.key_weaknesses = ai_data.get("key_weaknesses") or summary.key_weaknesses
                summary.buyer_pain_points = ai_data.get("buyer_pain_points") or summary.buyer_pain_points
                summary.summary_verdict = ai_data.get("summary_verdict") or summary.summary_verdict

        await db.flush()
        return summary

    async def get_domain_weakness_intelligence(
        self,
        db: AsyncSession,
        domain: str
    ) -> Dict[str, Any]:
        """
        Aggregate competitor product weaknesses and pain points across an entire store domain.
        Reveals competitor vulnerabilities across catalog items.
        """
        # Fetch summaries for products of this domain
        stmt = (
            select(ProductSentimentSummary, Product)
            .join(Product, ProductSentimentSummary.product_id == Product.id)
            .where(Product.source_domain == domain)
        )
        res = await db.execute(stmt)
        rows = res.all()

        if not rows:
            return {
                "domain": domain,
                "total_products_analyzed": 0,
                "weaknesses": [],
                "pain_points": [],
                "average_sentiment_positive": 0.0,
            }

        all_weaknesses = []
        all_pain_points = []
        pos_scores = []
        neg_scores = []

        for summary, product in rows:
            for w in (summary.key_weaknesses or []):
                all_weaknesses.append({"weakness": w, "product_name": product.name, "product_id": product.id})
            for p in (summary.buyer_pain_points or []):
                all_pain_points.append({"pain_point": p, "product_name": product.name, "product_id": product.id})
            pos_scores.append(summary.positive_percentage or 0.0)
            neg_scores.append(summary.negative_percentage or 0.0)

        avg_pos = round(sum(pos_scores) / len(pos_scores), 1) if pos_scores else 0.0
        avg_neg = round(sum(neg_scores) / len(neg_scores), 1) if neg_scores else 0.0

        return {
            "domain": domain,
            "total_products_analyzed": len(rows),
            "average_sentiment_positive": avg_pos,
            "average_sentiment_negative": avg_neg,
            "top_weaknesses": all_weaknesses[:15],
            "top_pain_points": all_pain_points[:15],
        }


review_sentiment_service = ReviewSentimentService()
