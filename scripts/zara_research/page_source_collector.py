"""Layer 2: Product Page Source Collector for Zara US.

Acquires public product page HTML and metadata using Playwright with Microsoft Edge.
Primary objective: minimize browser-side work.
Captures page.content() once and delegates all parsing to Layer 3.
Reuses browser page across items in a batch.
"""

from typing import Dict, Any, Optional
from playwright.sync_api import Page, Response

COOKIE_BANNER_DISMISSED = False


def dismiss_cookie_banner_if_present(page: Page) -> None:
    """Non-blocking cookie banner dismissal on first detection."""
    global COOKIE_BANNER_DISMISSED
    if COOKIE_BANNER_DISMISSED:
        return
    try:
        accept_btn = page.query_selector("#onetrust-accept-btn-handler, button#onetrust-accept-btn-handler")
        if accept_btn and accept_btn.is_visible():
            accept_btn.click()
            COOKIE_BANNER_DISMISSED = True
    except Exception:
        pass


def capture_product_page_source(page: Page, url: str, timeout_ms: int = 45000) -> Dict[str, Any]:
    """Navigate to public product URL and capture rendered HTML source bundle.
    
    Zero DOM round-trips for field extraction are performed here.
    Waits only until JSON-LD or heading selector is present, then captures page.content().
    
    Args:
        page: Playwright Page instance (reused across requests)
        url: Public Zara product URL
        timeout_ms: Navigation timeout in milliseconds
        
    Returns:
        bundle: Dict with keys:
            - html: Full rendered HTML content
            - final_url: URL after redirects
            - http_status: HTTP status code
            - page_title: Title of the rendered page
    """
    response: Optional[Response] = page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
    
    # Wait only until product structured data or main heading appears
    try:
        page.wait_for_selector('script[type="application/ld+json"], h1, .product-detail-view', timeout=4000)
    except Exception:
        pass

    dismiss_cookie_banner_if_present(page)

    final_url = page.url
    http_status = response.status if response else 200
    page_title = page.title()
    html_content = page.content()

    return {
        "url": url,
        "final_url": final_url,
        "http_status": http_status,
        "page_title": page_title,
        "html": html_content
    }
