"""Public reviewer preview: synthetic evidence, no network API, no secret leakage."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_static_preview_build_is_exact_allowlist():
    p = subprocess.run(
        [sys.executable, "scripts/build_public_preview.py"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert p.returncode == 0, p.stderr
    out = ROOT / "dist/public-preview"
    assert {x.name for x in out.iterdir()} == {
        "index.html", "preview.js", "preview.css", "cases.json", "style.css",
    }


def test_published_artifact_contains_no_secrets_or_write_capabilities():
    out = ROOT / "dist/public-preview"
    if not out.exists():
        subprocess.run([sys.executable, "scripts/build_public_preview.py"],
                       cwd=ROOT, check=True)
    text = "\n".join(p.read_text(encoding="utf-8") for p in out.iterdir())
    assert "dev-only-supervisor-token" not in text
    assert "dev-only-manager-token" not in text
    assert "SP_REPAIR_TOKEN" not in text
    assert "SP_ONCALL_WEBHOOK_TOKEN" not in text
    assert "postgresql+psycopg" not in text
    assert "http://127.0.0.1:18080" not in text
    assert "/api/v1/" not in text
    assert "localStorage" not in text
    assert "sessionStorage" not in text
    assert "fetch(\"./cases.json\"" in text
    assert "form-action 'none'" in text
    assert "SYNTHETIC_STATIC_PREVIEW" in text


def test_synced_source_fixture_and_true_late_minutes():
    data = json.loads((ROOT / "public_demo/cases.json").read_text())
    assert len(data["cases"]) == 2
    a, b = data["cases"]
    assert a["late_minutes"] == 72
    assert b["late_minutes"] == 102
    assert a["events"][1]["id"] == "msg-002"
    assert a["events"][2]["id"] == "msg-003"
    assert b["events"][1]["id"] == "case2-msg-002"
    assert b["events"][2]["id"] == "case2-msg-003"
    assert "SYNTHETIC" in data["mode"]
