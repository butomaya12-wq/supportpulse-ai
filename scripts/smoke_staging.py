"""Safe HTTP staging contract probe: no secret printing and no data mutation."""
import json
import os
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def request(base: str, path: str, token: str | None = None, method: str = "GET"):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = Request(base + path, headers=headers, method=method)
    try:
        with urlopen(req, timeout=20) as res:
            return res.status, json.loads(res.read(200_000))
    except HTTPError as exc:
        # Only status is relevant for negative tests; never echo token/body.
        return exc.code, None


def main():
    base = os.environ["STAGING_API_URL"].rstrip("/")
    parsed = urlparse(base)
    local_only = (os.environ.get("SP_CI_LOCAL_SMOKE") == "YES"
                  and parsed.hostname in {"127.0.0.1", "localhost"})
    if parsed.scheme != "https" and not (parsed.scheme == "http" and local_only):
        raise RuntimeError("Refusing staging probe without HTTPS")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RuntimeError("Refusing unsafe staging URL")
    token = os.environ["SP_STAGE_REVIEWER_TOKEN"]
    if len(token) < 48:
        raise RuntimeError("Reviewer token must be strong")
    status, health = request(base, "/health")
    assert status == 200 and health["production_ready"] is False
    assert request(base, "/api/v1/reviewer/overview")[0] == 401
    assert request(base, "/api/v1/reviewer/overview", "incorrect")[0] == 401
    status, ready = request(base, "/api/v1/reviewer/ready", token)
    assert status == 200 and ready["status"] == "ready", "Readiness failed"
    sha = os.environ.get("EXPECTED_STAGE_SHA")
    if sha and ready["release_sha"] != sha:
        raise AssertionError("Unexpected staging release SHA")
    status, overview = request(base, "/api/v1/reviewer/overview", token)
    assert status == 200 and overview["data"]["tenant"] == "demo-studio"
    assert overview["data"]["impact_rub"] is None
    assert overview["data"]["counts"]["review_backlog"] == 1
    status, findings = request(base, "/api/v1/reviewer/findings", token)
    assert status == 200 and len(findings["data"]) == 1
    assert findings["data"][0]["state"] == "CANDIDATE_OVERDUE"
    assert request(base, "/api/v1/demo/seed", token, method="POST")[0] == 404
    assert request(base, "/api/v1/demo/repair-drill/arm", token, method="POST")[0] == 404
    print("PASS: HTTPS/loopback staging read-only contract, auth fence and 1 synthetic case")
    print("Release SHA verified" if sha else "Release SHA not compared")


if __name__ == "__main__":
    main()
