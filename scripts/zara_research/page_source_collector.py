"""Layer 2: Product Page Source Collector for Zara US.

Acquires public product page HTML and metadata using Playwright with Microsoft Edge.
Primary objective: minimize browser-side work and maximize network throughput.
Captures page.content() once and delegates all parsing to Layer 3.
Supports both single-page synchronous capture and high-throughput concurrent async collection.
"""

import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from playwright.sync_api import Page as SyncPage, Response as SyncResponse
from playwright.async_api import async_playwright, Page as AsyncPage, Route

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
COOKIE_BANNER_DISMISSED = False


def clean_filename_id(product_id: str) -> str:
    """Normalize product_id for filesystem safety."""
    return product_id.replace(":", "_").replace("/", "_")


def save_page_source_bundle(output_dir: Path, product_id: str, html_content: str, metadata: Dict[str, Any]) -> Tuple[Path, Path]:
    """Atomically save raw HTML and metadata bundle to disk.
    
    Args:
        output_dir: Destination directory
        product_id: Zara product ID
        html_content: Raw rendered HTML string
        metadata: Metadata dictionary
        
    Returns:
        (html_path, meta_path)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    clean_id = clean_filename_id(product_id)
    html_path = output_dir / f"{clean_id}.html"
    meta_path = output_dir / f"{clean_id}.meta.json"

    # Atomic write HTML
    tmp_html = html_path.with_suffix(".html.tmp")
    tmp_html.write_text(html_content, encoding="utf-8")
    tmp_html.replace(html_path)

    # Atomic write metadata
    tmp_meta = meta_path.with_suffix(".meta.json.tmp")
    tmp_meta.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_meta.replace(meta_path)

    return html_path, meta_path


def dismiss_cookie_banner_if_present(page: SyncPage) -> None:
    """Non-blocking cookie banner dismissal on first detection (sync)."""
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


async def async_dismiss_cookie_banner(page: AsyncPage) -> None:
    """Non-blocking cookie banner dismissal on first detection (async)."""
    try:
        accept_btn = await page.query_selector("#onetrust-accept-btn-handler, button#onetrust-accept-btn-handler")
        if accept_btn and await accept_btn.is_visible():
            await accept_btn.click()
    except Exception:
        pass


async def async_route_interceptor(route: Route) -> None:
    """Route handler that aborts heavy media and tracking to maximize network throughput."""
    req = route.request
    url_lower = req.url.lower()
    if req.resource_type in ["font", "media", "image"]:
        await route.abort()
    elif any(tracker in url_lower for tracker in ["google-analytics", "doubleclick", "criteo", "tiqcdn", "clarity", "bing"]):
        await route.abort()
    else:
        await route.continue_()


def sync_wait_for_product_evidence(page: SyncPage, timeout_ms: int = 3000) -> Tuple[bool, str, int]:
    """Wait until sufficient product evidence exists in the DOM without 4-second invisible script penalty.
    
    Returns:
        (found, evidence_type, wait_duration_ms)
    """
    t0 = time.perf_counter()
    # 1. Check for JSON-LD script node attached to DOM
    try:
        page.wait_for_selector('script[type="application/ld+json"]', state="attached", timeout=timeout_ms)
        ms = int((time.perf_counter() - t0) * 1000)
        return True, "jsonld_attached", ms
    except Exception:
        pass

    # 2. Fallback to primary visible product container
    try:
        rem = max(500, timeout_ms - int((time.perf_counter() - t0) * 1000))
        page.wait_for_selector('h1, .product-detail-view, .product-detail-info, main', state="visible", timeout=rem)
        ms = int((time.perf_counter() - t0) * 1000)
        return True, "dom_container_visible", ms
    except Exception:
        pass

    ms = int((time.perf_counter() - t0) * 1000)
    return False, "timeout_fallback", ms


async def async_wait_for_product_evidence(page: AsyncPage, timeout_ms: int = 3000) -> Tuple[bool, str, int]:
    """Async wait until sufficient product evidence exists in the DOM.
    
    Returns:
        (found, evidence_type, wait_duration_ms)
    """
    t0 = time.perf_counter()
    # 1. Check for JSON-LD script node attached to DOM
    try:
        await page.wait_for_selector('script[type="application/ld+json"]', state="attached", timeout=timeout_ms)
        ms = int((time.perf_counter() - t0) * 1000)
        return True, "jsonld_attached", ms
    except Exception:
        pass

    # 2. Fallback to primary visible product container
    try:
        rem = max(500, timeout_ms - int((time.perf_counter() - t0) * 1000))
        await page.wait_for_selector('h1, .product-detail-view, .product-detail-info, main', state="visible", timeout=rem)
        ms = int((time.perf_counter() - t0) * 1000)
        return True, "dom_container_visible", ms
    except Exception:
        pass

    ms = int((time.perf_counter() - t0) * 1000)
    return False, "timeout_fallback", ms


def capture_product_page_source(page: SyncPage, url: str, timeout_ms: int = 45000) -> Dict[str, Any]:
    """Navigate to public product URL and capture rendered HTML source bundle (sync).
    
    Measures navigation and readiness wait times separately.
    """
    t_nav_0 = time.perf_counter()
    response: Optional[SyncResponse] = page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
    nav_time_ms = int((time.perf_counter() - t_nav_0) * 1000)
    
    found_evidence, evidence_type, ready_time_ms = sync_wait_for_product_evidence(page, timeout_ms=3000)
    dismiss_cookie_banner_if_present(page)

    t_cap_0 = time.perf_counter()
    final_url = page.url
    http_status = response.status if response else 200
    page_title = page.title()
    html_content = page.content()
    cap_time_ms = int((time.perf_counter() - t_cap_0) * 1000)

    return {
        "url": url,
        "final_url": final_url,
        "http_status": http_status,
        "page_title": page_title,
        "html": html_content,
        "navigation_time_ms": nav_time_ms,
        "readiness_wait_ms": ready_time_ms,
        "capture_time_ms": cap_time_ms,
        "readiness_type": evidence_type
    }


async def _fetch_worker(
    worker_id: int,
    queue: asyncio.Queue,
    page: AsyncPage,
    output_dir: Path,
    timeout_ms: int,
    results: List[Dict[str, Any]],
    stats: Dict[str, Any]
) -> None:
    """Worker coroutine that pulls URLs from queue, navigates, and saves source bundle."""
    first_item = True
    while True:
        item = await queue.get()
        if item is None:
            queue.task_done()
            break

        product_id = item["id"]
        url = item["url"]
        retries = 0
        max_retries = 1
        success = False

        while retries <= max_retries and not success:
            t0 = time.perf_counter()
            error_msg = None
            try:
                t_nav_0 = time.perf_counter()
                response = await page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                nav_time_ms = int((time.perf_counter() - t_nav_0) * 1000)

                # Explicit readiness wait: state="attached" for JSON-LD script
                found_ev, ev_type, ready_time_ms = await async_wait_for_product_evidence(page, timeout_ms=3000)

                if first_item:
                    await async_dismiss_cookie_banner(page)
                    first_item = False

                t_cap_0 = time.perf_counter()
                final_url = page.url
                http_status = response.status if response else 200
                page_title = await page.title()
                html_content = await page.content()
                cap_time_ms = int((time.perf_counter() - t_cap_0) * 1000)

                total_fetch_ms = int((time.perf_counter() - t0) * 1000)
                jsonld_present = 'application/ld+json' in html_content

                # Check for security challenges
                is_challenge = False
                challenge_reason = None
                if "Access Denied" in page_title or "access denied" in page_title.lower():
                    is_challenge = True
                    challenge_reason = "Access Denied"
                elif any(k in html_content.lower() for k in ["verify you are human", "security check", "cf-turnstile"]):
                    is_challenge = True
                    challenge_reason = "Verification challenge detected"

                if is_challenge:
                    stats["challenge_count"] += 1

                meta = {
                    "product_id": product_id,
                    "source_url": url,
                    "final_url": final_url,
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                    "browser_worker_id": worker_id,
                    "navigation_time_ms": nav_time_ms,
                    "readiness_wait_ms": ready_time_ms,
                    "capture_time_ms": cap_time_ms,
                    "total_fetch_ms": total_fetch_ms,
                    "readiness_type": ev_type,
                    "http_status": http_status,
                    "retry_count": retries,
                    "content_length": len(html_content),
                    "jsonld_present": jsonld_present,
                    "challenge_detected": is_challenge,
                    "challenge_reason": challenge_reason
                }

                save_page_source_bundle(output_dir, product_id, html_content, meta)
                results.append(meta)
                success = True
                stats["success_count"] += 1
                stats["nav_times_ms"].append(nav_time_ms)
                stats["ready_times_ms"].append(ready_time_ms)
                stats["capture_times_ms"].append(cap_time_ms)
                stats["total_fetch_times_ms"].append(total_fetch_ms)
                print(f"[Worker {worker_id}] -> {product_id} | Nav: {nav_time_ms}ms | Ready: {ready_time_ms}ms ({ev_type}) | Cap: {cap_time_ms}ms | {len(html_content):,} chars")

            except Exception as e:
                retries += 1
                error_msg = str(e)
                if retries <= max_retries:
                    print(f"[Worker {worker_id}] Retrying {product_id} (attempt {retries}): {error_msg}")
                    await asyncio.sleep(1.0)
                else:
                    total_fetch_ms = int((time.perf_counter() - t0) * 1000)
                    meta = {
                        "product_id": product_id,
                        "source_url": url,
                        "final_url": None,
                        "collected_at": datetime.now(timezone.utc).isoformat(),
                        "browser_worker_id": worker_id,
                        "navigation_time_ms": 0,
                        "readiness_wait_ms": 0,
                        "capture_time_ms": 0,
                        "total_fetch_ms": total_fetch_ms,
                        "readiness_type": "error",
                        "http_status": None,
                        "retry_count": retries,
                        "content_length": 0,
                        "jsonld_present": False,
                        "challenge_detected": False,
                        "error": error_msg
                    }
                    results.append(meta)
                    stats["fail_count"] += 1
                    print(f"[Worker {worker_id}] FAILED {product_id}: {error_msg}")

        queue.task_done()


async def run_concurrent_collection(
    product_items: List[Dict[str, Any]],
    concurrency_level: int,
    output_dir: Path,
    timeout_ms: int = 45000,
    headless: bool = False,
    edge_path: str = EDGE_PATH
) -> Dict[str, Any]:
    """Execute concurrent page source collection across N dedicated browser pages."""
    output_dir.mkdir(parents=True, exist_ok=True)
    queue: asyncio.Queue = asyncio.Queue()
    for item in product_items:
        await queue.put(item)

    results: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {
        "success_count": 0,
        "fail_count": 0,
        "challenge_count": 0,
        "nav_times_ms": [],
        "ready_times_ms": [],
        "capture_times_ms": [],
        "total_fetch_times_ms": []
    }

    t_start = time.perf_counter()

    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=edge_path, headless=headless)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
            viewport={"width": 1280, "height": 800}
        )

        # Route interception on context to block heavy binary assets across all pages
        await context.route("**/*", async_route_interceptor)

        pages = [await context.new_page() for _ in range(concurrency_level)]

        worker_tasks = [
            asyncio.create_task(
                _fetch_worker(i, queue, pages[i], output_dir, timeout_ms, results, stats)
            )
            for i in range(concurrency_level)
        ]

        # Put sentinel None to stop workers
        for _ in range(concurrency_level):
            await queue.put(None)

        await asyncio.gather(*worker_tasks)
        await browser.close()

    t_total = time.perf_counter() - t_start

    def calc_stats(lst):
        if not lst:
            return 0.0, 0.0, 0.0, 0, 0
        avg = sum(lst) / len(lst)
        s = sorted(lst)
        med = s[len(s) // 2]
        p95 = s[min(int(len(s) * 0.95), len(s) - 1)]
        return round(avg, 1), round(med, 1), round(p95, 1), min(s), max(s)

    avg_nav, med_nav, p95_nav, min_nav, max_nav = calc_stats(stats["nav_times_ms"])
    avg_ready, med_ready, p95_ready, min_ready, max_ready = calc_stats(stats["ready_times_ms"])
    avg_cap, med_cap, p95_cap, min_cap, max_cap = calc_stats(stats["capture_times_ms"])
    avg_fetch, med_fetch, p95_fetch, min_fetch, max_fetch = calc_stats(stats["total_fetch_times_ms"])

    summary = {
        "concurrency_level": concurrency_level,
        "total_items": len(product_items),
        "success_count": stats["success_count"],
        "fail_count": stats["fail_count"],
        "challenge_count": stats["challenge_count"],
        "total_wall_time_sec": round(t_total, 2),
        "throughput_pages_per_sec": round(len(product_items) / t_total, 2) if t_total > 0 else 0.0,
        "avg_nav_time_ms": avg_nav,
        "median_nav_time_ms": med_nav,
        "p95_nav_time_ms": p95_nav,
        "avg_readiness_wait_ms": avg_ready,
        "median_readiness_wait_ms": med_ready,
        "p95_readiness_wait_ms": p95_ready,
        "avg_capture_time_ms": avg_cap,
        "median_capture_time_ms": med_cap,
        "p95_capture_time_ms": p95_cap,
        "avg_total_fetch_ms": avg_fetch,
        "median_total_fetch_ms": med_fetch,
        "p95_total_fetch_ms": p95_fetch,
        "min_nav_time_ms": min_nav,
        "max_nav_time_ms": max_nav,
        "results": results
    }

    return summary


def collect_page_sources_concurrent(
    product_items: List[Dict[str, Any]],
    concurrency_level: int,
    output_dir: Path,
    timeout_ms: int = 45000,
    headless: bool = False,
    edge_path: str = EDGE_PATH
) -> Dict[str, Any]:
    """Synchronous entrypoint to run async concurrent page collection."""
    return asyncio.run(
        run_concurrent_collection(
            product_items=product_items,
            concurrency_level=concurrency_level,
            output_dir=output_dir,
            timeout_ms=timeout_ms,
            headless=headless,
            edge_path=edge_path
        )
    )
