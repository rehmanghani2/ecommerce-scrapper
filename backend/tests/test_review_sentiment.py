"""
Unit and integration tests for Customer Review & Competitor Sentiment Mining.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import Response
from app.services.review_sentiment_service import ReviewSentimentService, review_sentiment_service
from app.models.product import Product, ProductReview, ProductSentimentSummary


def test_heuristic_sentiment_positive():
    service = ReviewSentimentService()
    content = "I absolutely love these headphones! The sound quality is great and battery life is awesome."
    sentiment, score, topics = service.analyze_review_heuristic(content, rating=5.0)

    assert sentiment == "positive"
    assert score > 0.4
    assert "sound quality" in topics
    assert "battery life" in topics


def test_heuristic_sentiment_negative():
    service = ReviewSentimentService()
    content = "Terrible product. It broke after two days and the build quality feels cheap and flimsy."
    sentiment, score, topics = service.analyze_review_heuristic(content, rating=1.0)

    assert sentiment == "negative"
    assert score < -0.4
    assert "build quality" in topics


def test_heuristic_sentiment_neutral():
    service = ReviewSentimentService()
    content = "Standard item as described. Arrived in a box."
    sentiment, score, topics = service.analyze_review_heuristic(content, rating=3.0)

    assert sentiment == "neutral"
    assert -0.25 <= score <= 0.25


@pytest.mark.asyncio
async def test_analyze_with_ai_mock():
    service = ReviewSentimentService()
    mock_res = MagicMock(spec=Response)
    mock_res.status_code = 200
    mock_res.json = MagicMock(return_value={
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": (
                                '{"positive_percentage": 75.0, "neutral_percentage": 10.0, "negative_percentage": 15.0, '
                                '"key_strengths": ["Industry-leading ANC", "Exceptional comfort"], '
                                '"key_weaknesses": ["Hinge feels fragile", "Microphone picks up wind"], '
                                '"buyer_pain_points": ["App connection drops", "Bulky carrying case"], '
                                '"summary_verdict": "Strong consumer praise for acoustics, but hardware durability concerns remain."}'
                            )
                        }
                    ]
                }
            }
        ]
    })

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_res
        reviews = [
            {"rating": 5.0, "title": "Great", "content": "Awesome ANC"},
            {"rating": 2.0, "title": "Fragile", "content": "Hinge broke"}
        ]
        res = await service.analyze_with_ai("Sony Headphones", reviews, api_key="test-key")
        assert res["success"] is True
        assert res["positive_percentage"] == 75.0
        assert "Hinge feels fragile" in res["key_weaknesses"]
        assert "Industry-leading ANC" in res["key_strengths"]


@pytest.mark.asyncio
async def test_recalculate_sentiment_summary():
    service = ReviewSentimentService()
    p = Product(id=1, name="Test Phone")

    r1 = ProductReview(id=10, product_id=1, rating=5.0, sentiment="positive", key_topics=["battery life"])
    r2 = ProductReview(id=11, product_id=1, rating=4.0, sentiment="positive", key_topics=["camera"])
    r3 = ProductReview(id=12, product_id=1, rating=1.0, sentiment="negative", key_topics=["overheating"])

    mock_db = AsyncMock()
    mock_db.get.return_value = p

    # Mock execute for reviews
    mock_res_rev = MagicMock()
    mock_res_rev.scalars.return_value.all.return_value = [r1, r2, r3]

    # Mock execute for summary check (returns None initially)
    mock_res_sum = MagicMock()
    mock_res_sum.scalar_one_or_none.return_value = None

    mock_db.execute.side_effect = [mock_res_rev, mock_res_sum]

    summary = await service.recalculate_sentiment_summary(mock_db, 1, run_ai=False)
    assert summary is not None
    assert summary.total_reviews_analyzed == 3
    assert summary.average_rating == round((5.0 + 4.0 + 1.0) / 3.0, 2)
    assert summary.positive_percentage == round((2 / 3) * 100, 1)
    assert summary.negative_percentage == round((1 / 3) * 100, 1)
    assert any("overheating" in w for w in summary.key_weaknesses)


@pytest.mark.asyncio
async def test_reviews_api_endpoints():
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test Ingest Reviews
        payload = {
            "reviews": [
                {
                    "author": "Alice",
                    "rating": 5.0,
                    "title": "Superb",
                    "content": "Excellent sound quality and fast shipping!",
                    "verified_purchase": True
                },
                {
                    "author": "Bob",
                    "rating": 2.0,
                    "title": "Cheap quality",
                    "content": "Terrible plastic feel and broke immediately.",
                    "verified_purchase": False
                }
            ],
            "run_ai_analysis": False
        }

        with patch("app.services.review_sentiment_service.review_sentiment_service.ingest_reviews", new_callable=AsyncMock) as mock_ingest:
            mock_ingest.return_value = {"success": True, "reviews_added": 2}
            res = await client.post("/api/v1/products/42/reviews", json=payload)
            assert res.status_code == 200
            assert res.json()["reviews_added"] == 2

        # Test Sentiment Analysis trigger
        with patch("app.services.review_sentiment_service.review_sentiment_service.recalculate_sentiment_summary", new_callable=AsyncMock) as mock_analyze:
            dummy_summary = ProductSentimentSummary(
                id=1,
                product_id=42,
                total_reviews_analyzed=10,
                average_rating=4.2,
                positive_percentage=80.0,
                neutral_percentage=10.0,
                negative_percentage=10.0,
                key_strengths=["High sound quality"],
                key_weaknesses=["Plastic hinge flaw"],
                buyer_pain_points=["Tight fit"],
                summary_verdict="Highly positive"
            )
            mock_analyze.return_value = dummy_summary
            res = await client.post("/api/v1/products/42/sentiment/analyze", json={"use_ai": False})
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
            assert data["sentiment_summary"]["positive_percentage"] == 80.0
