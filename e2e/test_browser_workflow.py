"""Real Chromium browser tests against a disposable synthetic-only PostgreSQL service.

Never point E2E_BASE_URL at a shared/live app. CI supplies an isolated Postgres database.
"""
import os
import re
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:18080").rstrip("/")
TOKEN = os.environ.get("E2E_SUPERVISOR_TOKEN", "isolated-e2e-supervisor")
ARTIFACTS = Path("artifacts/browser-e2e")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    result = outcome.get_result()
    setattr(item, "rep_" + result.when, result)


@pytest.fixture(autouse=True)
def isolated_database_guard():
    """Make accidental runs against the owner's persistent local database impossible."""
    assert os.getenv("SUPPORTPULSE_E2E_ISOLATED") == "YES", (
        "Browser E2E requires SUPPORTPULSE_E2E_ISOLATED=YES and disposable DB"
    )
    assert "supportpulse_e2e" in os.getenv("DATABASE_URL", ""), (
        "Browser E2E must use its disposable supportpulse_e2e PostgreSQL database"
    )
    assert BASE.startswith("http://127.0.0.1:") or BASE.startswith("http://localhost:"), (
        "Browser E2E is restricted to localhost"
    )


@pytest.fixture
def page(request):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000},
            locale="ru-RU",
            timezone_id="Europe/Moscow",
        )
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        browser_page = context.new_page()
        try:
            yield browser_page
        finally:
            outcome = getattr(request.node, "rep_call", None)
            if outcome is not None and outcome.failed:
                ARTIFACTS.mkdir(parents=True, exist_ok=True)
                basename = re.sub(r"[^a-zA-Z0-9_-]", "-", request.node.name)
                browser_page.screenshot(path=str(ARTIFACTS / f"{basename}.png"), full_page=True)
                context.tracing.stop(path=str(ARTIFACTS / f"{basename}-trace.zip"))
            else:
                context.tracing.stop()
            context.close()
            browser.close()


def api_post(page, path, data):
    response = page.request.post(
        f"{BASE}/api/v1/{path}",
        headers={"Authorization": f"Bearer {TOKEN}"},
        data=data,
    )
    assert response.status == 200, f"{path}: HTTP {response.status} {response.text()}"
    return response.json()


def api_get(page, path):
    response = page.request.get(
        f"{BASE}/api/v1/{path}",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status == 200, f"{path}: HTTP {response.status} {response.text()}"
    return response.json()


def connect(page):
    page.goto(BASE + "/")
    page.locator("#token").fill(TOKEN)
    page.locator("#connect").click()
    expect(page.locator("#message")).to_contain_text("Подключено")


def open_case(page, conversation):
    row = page.locator(".case-row").filter(has_text=conversation)
    expect(row).to_have_count(1)
    row.get_by_role("button", name=re.compile("Открыть")).click()
    expect(page.locator("#detailTitle")).to_contain_text(conversation)


def test_browser_complete_evidence_first_workflow_and_persistence(page):
    """Drive original UI from seed -> review -> assignment -> import -> verify."""
    connect(page)
    page.locator("#seed").click()
    expect(page.locator("#casesList")).to_contain_text("demo-lead-001")
    open_case(page, "demo-lead-001")
    expect(page.locator("#detailPanel")).to_contain_text("На проверку")

    page.once("dialog", lambda dialog: dialog.accept(
        "Нет подтверждённого расчёта в синхронизированном источнике после обещанного срока."
    ))
    page.locator("#confirm").click()
    expect(page.locator("#detailPanel")).to_contain_text("Просрочка подтверждена")
    page.locator("#assign").click()
    expect(page.locator("#detailContent")).to_contain_text("OPEN")
    expect(page.locator("#detailActions")).to_contain_text(
        "Подтверждающего события отправки пока нет"
    )
    expect(page.locator("#verify")).to_have_count(0)
    expect(page.locator("#detailActions").get_by_role("link", name=re.compile("Перейти к импорту"))).to_be_visible()

    # A forged provider ID is rejected by the backend before import.
    before = api_get(page, "findings/1")
    action_id = before["corrective_action"]["id"]
    bad = page.request.post(
        f"{BASE}/api/v1/actions/{action_id}/verify",
        headers={"Authorization": f"Bearer {TOKEN}"},
        data={"proof_external_id": "msg-003"},
    )
    assert bad.status == 409
    assert api_get(page, "findings/1")["corrective_action"]["state"] == "OPEN"

    page.locator("#followup").click()
    expect(page.locator("#detailContent")).to_contain_text("msg-003")
    expect(page.locator("#verify")).to_be_visible()
    expect(page.locator("#verify")).to_contain_text("msg-003")
    expect(page.locator("#detailActions")).to_contain_text(
        "не получение расчёта клиентом или оплата"
    )
    page.locator("#verify").click()

    expect(page.locator("#detailContent")).to_contain_text("VERIFIED")
    expect(page.locator("#detailPanel")).to_contain_text("Отправлено поздно")
    expect(page.locator("#verifiedCount")).to_have_text("1")
    expect(page.locator("#rateBasis")).to_contain_text("Синтетических кейсов")
    expect(page.locator("#detailContent")).to_contain_text("Финансовая потеря:")
    expect(page.locator("#detailContent")).to_contain_text("неизвестна")
    done = api_get(page, "findings/1")
    assert done["state"] == "CORRECTED_LATE"
    assert done["corrective_action"]["state"] == "VERIFIED"
    assert done["verification"]["reason"] == "ALREADY_VERIFIED"
    assert any(
        event["action"] == "ACTION_CLOSED" and event["target"] == "finding:1"
        for event in api_get(page, "audit")["data"]
    )
    assert api_get(page, "overview")["impact_rub"] is None

    # Browser reload performs a fresh authenticated read from persistent Postgres.
    connect(page)
    open_case(page, "demo-lead-001")
    expect(page.locator("#detailContent")).to_contain_text("VERIFIED")
    expect(page.locator("#verify")).to_have_count(0)


def test_browser_wrong_actor_and_bounced_proof_remain_blocked(page):
    """Wrong actor does not count; a bounced send does not count as correction."""
    source = "e2e-negative-source"
    conversation = "e2e-negative-lead"
    api_post(page, "imports", {
        "source_id": source,
        "channel": "instagram-synthetic",
        "watermark": "2026-10-22T14:30:00Z",
        "healthy": True,
        "events": [
            {
                "external_id": "neg-customer",
                "event_time": "2026-10-22T07:05:00Z",
                "kind": "customer_message",
                "conversation_id": conversation,
                "actor_id": "synthetic-buyer",
                "message": "Запросила цену мебели."
            },
            {
                "external_id": "neg-promise",
                "event_time": "2026-10-22T07:18:00Z",
                "kind": "manager_message",
                "conversation_id": conversation,
                "actor_id": "demo-manager-001",
                "message": "Пришлю расчёт до 16:00."
            },
            {
                "external_id": "neg-wrong-actor",
                "event_time": "2026-10-22T14:12:00Z",
                "kind": "quote_sent",
                "conversation_id": conversation,
                "actor_id": "another-manager",
                "message": "Чужая отправка не должна подтверждать обещание."
            },
        ],
    })
    api_post(page, "commitments", {
        "source_id": source,
        "basis_external_id": "neg-promise",
        "due_at": "2026-10-22T16:00:00+03:00",
        "action_type": "send_quote",
    })
    evaluated = api_post(page, "evaluate?as_of=2026-10-22T14:30:00Z", {})
    case = next(
        item for item in api_get(page, "findings")["data"]
        if item["commitment"]["conversation_id"] == conversation
    )
    assert case["state"] == "CANDIDATE_OVERDUE"
    case_id = case["id"]
    api_post(page, f"findings/{case_id}/review", {
        "decision": "CONFIRM",
        "reason": "В исходной переписке нет отправки от ответственного менеджера.",
    })
    action = api_post(page, f"findings/{case_id}/actions", {
        "owner_id": "demo-manager-001"
    })["action_id"]
    assert api_get(page, f"findings/{case_id}")["verification"]["reason"] == "NO_SOURCE_PROOF"

    connect(page)
    open_case(page, conversation)
    expect(page.locator("#verify")).to_have_count(0)
    expect(page.locator("#detailActions")).to_contain_text("пока нет")

    # Even with a real quote_sent event, a bounce blocks verification.
    api_post(page, "imports", {
        "source_id": source,
        "channel": "instagram-synthetic",
        "watermark": "2026-10-22T15:00:00Z",
        "healthy": True,
        "events": [
            {
                "external_id": "neg-quote",
                "event_time": "2026-10-22T14:40:00Z",
                "kind": "quote_sent",
                "conversation_id": conversation,
                "actor_id": "demo-manager-001",
                "message": "Расчёт отправлен."
            },
            {
                "external_id": "neg-bounce",
                "event_time": "2026-10-22T14:41:00Z",
                "kind": "quote_bounced",
                "conversation_id": conversation,
                "actor_id": "demo-manager-001",
                "message": "Письмо вернулось."
            },
        ],
    })
    api_post(page, "evaluate?as_of=2026-10-22T15:00:00Z", {})
    page.locator("#refresh").click()
    expect(page.locator("#detailActions")).to_contain_text(
        "Источник сообщил об ошибке доставки"
    )
    expect(page.locator("#verify")).to_have_count(0)
    assert api_get(page, f"findings/{case_id}")["verification"]["reason"] == "BOUNCED"
    attempted = page.request.post(
        f"{BASE}/api/v1/actions/{action}/verify",
        headers={"Authorization": f"Bearer {TOKEN}"},
        data={"proof_external_id": "neg-quote"},
    )
    assert attempted.status == 409
    assert api_get(page, f"findings/{case_id}")["corrective_action"]["state"] == "OPEN"
    assert not any(
        item["action"] == "ACTION_CLOSED" and item["target"] == f"finding:{case_id}"
        for item in api_get(page, "audit")["data"]
    )
