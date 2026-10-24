"""Build the PUBLIC READ-ONLY reviewer frontend from a strict file allowlist.

No local .env, database, source code, private tokens or APIs are copied. The
public cases.json is 100% synthetic and validated against original fixtures.
"""
from pathlib import Path
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "public-preview"
BASE = ROOT / "public_demo"

COPY = {
    BASE / "index.html": "index.html",
    BASE / "preview.js": "preview.js",
    BASE / "preview.css": "preview.css",
    BASE / "cases.json": "cases.json",
    ROOT / "app/static/style.css": "style.css",
}
FORBIDDEN = (
    b"dev-only-supervisor-token", b"dev-only-manager-token",
    b"SP_ONCALL_WEBHOOK_TOKEN", b"SP_REPAIR_TOKEN",
    b"POSTGRES_PASSWORD", b"postgresql+psycopg://",
    b"/api/v1/demo/repair-drill", b"/api/v1/imports",
    b"/api/v1/commitments", b"Authorization: Bearer",
)


def verify_source_data():
    data = json.loads((BASE / "cases.json").read_text(encoding="utf-8"))
    initial = json.loads((ROOT / "fixtures/initial.json").read_text(encoding="utf-8"))
    followup = json.loads((ROOT / "fixtures/followup.json").read_text(encoding="utf-8"))
    assert data["mode"] == "SYNTHETIC_STATIC_PREVIEW" and len(data["cases"]) == 2
    a, b = data["cases"]
    assert a["source_id"] == initial["import"]["source_id"]
    assert a["due_at"] == "2026-10-22T13:00:00Z"
    assert a["events"][:2] == [
        {"id": x["external_id"], "kind": x["kind"], "at": x["event_time"], "message": x["message"]}
        for x in initial["import"]["events"]
    ]
    assert a["events"][2] == {
        "id": followup["import"]["events"][0]["external_id"],
        "kind": followup["import"]["events"][0]["kind"],
        "at": followup["import"]["events"][0]["event_time"],
        "message": followup["import"]["events"][0]["message"],
    }
    assert all(x["channel"] == "instagram-synthetic" and x["manager"] == "demo-manager-001" for x in (a, b))
    assert all(len(x["events"]) == 3 and x["events"][1]["kind"] == "manager_message"
               and x["events"][2]["kind"] == "quote_sent" for x in (a, b))
    assert b["id"] == 2 and b["conversation_id"] == "demo-lead-002"
    from datetime import datetime
    for x in (a, b):
        due = datetime.fromisoformat(x["due_at"].replace("Z", "+00:00"))
        sent = datetime.fromisoformat(x["sent_at"].replace("Z", "+00:00"))
        assert int((sent - due).total_seconds() / 60) == x["late_minutes"] > 0
    return data


def build():
    verify_source_data()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    for source, dest in COPY.items():
        if source.is_symlink() or not source.is_file():
            raise RuntimeError("Unsafe public bundle input " + source.name)
        data = source.read_bytes()
        for secret in FORBIDDEN:
            if secret in data:
                raise RuntimeError("Sensitive API/secret pattern detected in " + dest)
        (OUT / dest).write_bytes(data)
    actual = {p.name for p in OUT.iterdir()}
    if actual != set(COPY.values()):
        raise RuntimeError("Unexpected public artifact contents")
    print("Built read-only synthetic reviewer preview (5 static files, no API or credentials).")


if __name__ == "__main__":
    build()
