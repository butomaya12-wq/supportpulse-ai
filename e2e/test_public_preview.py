"""Public static reviewer app stays interactive, while exposing no backend writes."""
import os
from playwright.sync_api import sync_playwright


def test_public_preview_opens_case_evidence_with_no_api_requests():
    url = os.environ.get("PUBLIC_PREVIEW_E2E_URL")
    assert url and url.startswith("http://127.0.0.1:"), "isolated preview URL only"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        requests = []
        page.on("request", lambda request: requests.append(request.url))
        response = page.goto(url, wait_until="networkidle")
        assert response.status == 200
        assert page.get_by_text("Обещания под контролем.").is_visible()
        assert page.locator("#case-list .case-row").count() == 2
        assert page.get_by_text("Синтетические кейсы", exact=False).count() > 0
        page.locator("#case-list .button").nth(1).click()
        assert "demo-lead-002" in page.locator("#detailTitle").inner_text()
        assert page.get_by_text("case2-msg-003", exact=False).count() > 0
        page.get_by_role("button", name="2 · Подтверждённая просрочка").click()
        assert page.get_by_text("Просрочка подтверждена человеком").is_visible()
        assert page.get_by_text("case2-msg-003", exact=False).count() == 0
        page.get_by_role("button", name="3 · Исправлено поздно").click()
        assert page.get_by_text("case2-msg-003", exact=False).count() > 0
        assert all("/api/" not in u for u in requests), requests
        assert all(u.startswith(url.rstrip("/")) for u in requests), requests
        browser.close()
