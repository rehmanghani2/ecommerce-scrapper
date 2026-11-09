import pytest

from app.core.challenge_detector import detect_challenge


def test_detects_cloudflare_interstitial():
    html = """
    <html><head><title>Just a moment...</title></head>
    <body><div id="cf-challenge-running">Checking your browser</div>
    <script src="/cdn-cgi/challenge-platform/scripts/jsd/main.js"></script>
    </body></html>
    """
    result = detect_challenge("https://shop.example/products", 200, html)

    assert result is not None
    assert result["provider"] == "cloudflare"
    assert result["confidence"] >= 0.9
    assert "provider_signature:cloudflare" in result["signals"]


def test_detects_datadome_challenge():
    html = """
    <html><body>
    <h1>Please verify you are human</h1>
    <script src="https://js.datadome.co/tags.js"></script>
    </body></html>
    """
    result = detect_challenge("https://shop.example/category", 403, html)

    assert result is not None
    assert result["provider"] == "datadome"


def test_detects_hcaptcha_interstitial():
    html = """
    <html><body>
    <p>Complete the CAPTCHA to continue</p>
    <iframe src="https://hcaptcha.com/1/api.js"></iframe>
    </body></html>
    """
    result = detect_challenge("https://shop.example/", 200, html)

    assert result is not None
    assert result["provider"] == "hcaptcha"


def test_does_not_flag_normal_contact_form_with_recaptcha():
    html = """
    <html><body>
    <h1>Contact us</h1>
    <form><div class="g-recaptcha"></div></form>
    </body></html>
    """
    assert detect_challenge("https://shop.example/contact", 200, html) is None


def test_does_not_flag_normal_product_copy_mentioning_captcha():
    html = """
    <html><body>
    <h1>Security camera</h1>
    <p>This product guide explains CAPTCHA technology.</p>
    </body></html>
    """
    assert detect_challenge("https://shop.example/product/camera", 200, html) is None


def test_returns_none_without_html():
    assert detect_challenge("https://shop.example/", 403, None) is None
