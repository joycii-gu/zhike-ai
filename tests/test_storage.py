"""Smoke tests for W4 durable storage and account isolation."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile


with tempfile.TemporaryDirectory() as directory:
    os.environ["ZHIKE_DATABASE_PATH"] = str(Path(directory) / "zhike-test.db")

    from src import storage

    storage.DATABASE_PATH = Path(os.environ["ZHIKE_DATABASE_PATH"])
    storage.initialize_database()

    alice = storage.create_user("alice@example.com", "Alice", "safe-pass-1")
    bob = storage.create_user("bob@example.com", "Bob", "safe-pass-2")
    assert storage.authenticate_user("alice@example.com", "safe-pass-1")["id"] == alice["id"]
    assert storage.authenticate_user("alice@example.com", "wrong") is None

    customer_id = storage.create_customer(
        alice["id"], "李总", "预算尚未确认，计划下周沟通。",
        {"industry": "企业培训", "stage": "需求探索", "priority": "高", "risk": "预算待确认"},
    )
    storage.save_report(
        alice["id"], customer_id,
        {"customer_profile": "ok", "need_analysis": "ok", "opportunity_assessment": "ok", "follow_up_plan": "ok", "communication_script": "ok", "daily_report": "ok"},
        [{"name": "客户解析", "status": "api", "runtime": "test"}], "test",
    )
    assert len(storage.list_customers(alice["id"])) == 1
    assert storage.list_customers(bob["id"]) == []
    assert storage.get_customer(bob["id"], customer_id) is None

    task_id = storage.create_task(alice["id"], customer_id, "确认下周沟通档期")
    storage.update_task_status(alice["id"], task_id, "已完成")
    assert storage.list_tasks(alice["id"], include_done=True)[0]["status"] == "已完成"

    event_id = storage.record_feedback_event(alice["id"], customer_id, "effective_communication", "客户确认演示时间")
    assert storage.dashboard_snapshot(alice["id"])["effective_communications"] == 1
    storage.revert_feedback_event(alice["id"], event_id)
    assert storage.dashboard_snapshot(alice["id"])["effective_communications"] == 0

print("W4 storage tests passed")
