from fastapi.testclient import TestClient

from api.server import app


client = TestClient(app)


def test_unified_api_preserves_gameconfig_health() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_unified_api_exposes_quality_review() -> None:
    response = client.post(
        "/api/quality/review",
        json={
            "diff": (
                "diff --git a/client.go b/client.go\n"
                "--- a/client.go\n"
                "+++ b/client.go\n"
                "@@ -1,1 +1,2 @@\n"
                " package demo\n"
                "+resp, err := http.Get(url)\n"
            ),
            "language": "go",
            "mode": "mock",
            "workflow": "dual_agent",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["findings"]
    assert [run["agent_name"] for run in payload["agent_runs"]] == [
        "review_agent",
        "test_agent",
    ]

