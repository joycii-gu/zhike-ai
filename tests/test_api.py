"""Smoke tests for the ECS FastAPI surface using the local Skills workflow."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ["ZHIKE_ENV"] = "development"
os.environ["ZHIKE_COOKIE_SECURE"] = "false"
os.environ["ZHIKE_DATABASE_PATH"] = str(Path(tempfile.gettempdir()) / "zhike-api-test.db")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402
from backend.main import app  # noqa: E402


def run_smoke_test() -> None:
    with TestClient(app) as client:
        # Entering visitor mode only creates a separate account. It must not
        # create business data or request the model runtime.
        response = client.post("/api/auth/guest")
        assert response.status_code == 201, response.text
        assert response.json()["user"]["is_guest"] is True
        response = client.get("/api/auth/me")
        assert response.status_code == 200 and response.json()["is_guest"] is True, response.text
        response = client.get("/api/customers")
        assert response.status_code == 200 and response.json() == [], response.text
        client.post("/api/auth/logout")

        response = client.post(
            "/api/auth/register",
            json={"email": "ecs-smoke@example.com", "display_name": "ECS 测试", "password": "safe-password-123"},
        )
        assert response.status_code in {201, 400}, response.text
        if response.status_code == 400:
            response = client.post("/api/auth/login", json={"email": "ecs-smoke@example.com", "password": "safe-password-123"})
            assert response.status_code == 200, response.text

        response = client.post(
            "/api/analysis",
            json={"customer_name": "李总", "raw_note": "李总想了解 AI 如何帮助企业培训销售团队跟进客户，希望下周线上沟通。", "force_mock": True},
        )
        assert response.status_code == 201, response.text
        customer_id = response.json()["customer_id"]
        assert customer_id

        # Existing W2 mock output must not leak into an account's W4 daily
        # view, even when the underlying report was produced in Mock mode.
        response = client.get(f"/api/customers/{customer_id}")
        assert response.status_code == 200, response.text
        daily_report = response.json()["report"]["daily_report"]
        assert "王经理" not in daily_report
        assert "陈老师" not in daily_report
        assert "李总" in daily_report

        # Legacy Markdown section headings must never be presented as a task
        # action to the businessperson.
        response = client.post(
            "/api/tasks",
            json={"customer_id": customer_id, "title": "# 跟进建议清单"},
        )
        assert response.status_code == 201, response.text
        response = client.get("/api/tasks?include_done=true")
        assert response.status_code == 200, response.text
        assert response.json()[0]["title"] == "查看客户分析并确认下一步行动"

        # W4 low-input flow: a one-sentence post-conversation update creates
        # only a reviewable action draft. A task exists only after confirmation.
        response = client.post(
            "/api/captures",
            json={"customer_name": "李总", "capture": "已确认下周三线上演示，预算仍待确认。", "force_mock": True},
        )
        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["action_draft"]["status"] == "待确认"
        assert payload["customer"]["name"] == "李总"

        response = client.post("/api/action-drafts/confirm", json={"draft_id": payload["action_draft"]["id"]})
        assert response.status_code == 200, response.text
        assert response.json()["customer_id"] == payload["customer_id"]

        response = client.get("/api/dashboard")
        assert response.status_code == 200, response.text
        assert response.json()["customer_count"] >= 1


if __name__ == "__main__":
    run_smoke_test()
    print("FastAPI ECS smoke test passed")
