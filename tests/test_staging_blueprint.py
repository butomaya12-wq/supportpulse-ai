"""The Render draft is safe to review but must not provision on merge."""
from pathlib import Path
import yaml


def test_staging_blueprint_has_no_prod_or_secret_values():
    path = Path(__file__).resolve().parents[1] / "render.staging.yaml"
    blueprint = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert list(blueprint) == ["services"]  # Postgres is provisioned/sealed separately
    assert len(blueprint["services"]) == 1
    s = blueprint["services"][0]
    assert s["name"] == "supportpulse-ai-stage-reader"
    assert s["plan"] == "free" and s["runtime"] == "docker"
    assert s["branch"] == "main"
    assert s["autoDeployTrigger"] == "checksPass"
    assert s["dockerfilePath"] == "./Dockerfile.staging"
    values = {e["key"]: e for e in s["envVars"]}
    assert values["SP_MODE"]["value"] == "synthetic_staging"
    assert values["SP_STAGING_SYNTHETIC_ONLY"]["value"] == "YES"
    assert values["SP_STAGE_ALLOWED_HOSTS"]["value"] == "supportpulse-ai-stage-reader.onrender.com"
    for secret in ("DATABASE_URL", "SP_STAGE_REVIEWER_TOKEN"):
        assert values[secret] == {"key": secret, "sync": False}
    assert all("production" not in str(e).lower() for e in blueprint["services"])
