from typing import List, Optional, Tuple

from wjx.network.browser_driver import BrowserDriver, create_playwright_driver as _browser_create_playwright_driver


def create_playwright_driver(
    headless: bool = False,
    prefer_browsers: Optional[List[str]] = None,
    proxy_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    window_position: Optional[Tuple[int, int]] = None,
) -> Tuple[BrowserDriver, str]:
    """Delegate to browser_driver implementation (Playwright-only)."""
    return _browser_create_playwright_driver(
        headless=headless,
        prefer_browsers=prefer_browsers,
        proxy_address=proxy_address,
        user_agent=user_agent,
        window_position=window_position,
    )
