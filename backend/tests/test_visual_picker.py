import pytest
from app.services.visual_picker_service import visual_picker_service
from app.models.selector_preset import SelectorPreset


def test_rewrite_srcset():
    base_url = "https://example.com/catalog"
    srcset = "image-small.jpg 300w, /media/image-large.jpg 1000w"
    rewritten = visual_picker_service._rewrite_srcset(srcset, base_url)
    assert "https://example.com/image-small.jpg 300w" in rewritten
    assert "https://example.com/media/image-large.jpg 1000w" in rewritten


@pytest.mark.asyncio
async def test_test_custom_selectors():
    # Test selector evaluation using local HTML sample
    test_html = """
    <html>
        <body>
            <div class="product-item">
                <h2 class="title">Running Shoe A</h2>
                <span class="price">$59.99</span>
                <img src="/img/shoe1.jpg" />
                <a class="item-link" href="/product/1">View</a>
            </div>
            <div class="product-item">
                <h2 class="title">Running Shoe B</h2>
                <span class="price">$79.99</span>
                <img src="/img/shoe2.jpg" />
                <a class="item-link" href="/product/2">View</a>
            </div>
        </body>
    </html>
    """

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(test_html, "html.parser")
    elements = soup.select(".product-item")
    assert len(elements) == 2
    assert elements[0].select_one(".title").get_text(strip=True) == "Running Shoe A"
    assert elements[0].select_one(".price").get_text(strip=True) == "$59.99"


def test_selector_preset_model():
    preset = SelectorPreset(
        name="Nike Store Recipe",
        domain="nike.com",
        description="Extracts shoe catalog",
        selectors='{"product_card": ".product-card", "product_name": ".card-title"}'
    )
    assert preset.name == "Nike Store Recipe"
    assert preset.domain == "nike.com"
    assert "product_card" in preset.selectors
