"""SQLite persistence layer for the ZhiKe AI W4 application.

The module deliberately keeps authentication and business data behind a small
repository API.  SQLite is the W4 single-server default; a hosted Postgres
adapter can replace this module later without changing Agent logic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import pbkdf2_hmac
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile
from typing import Any
from uuid import uuid4


# Do not depend on the process working directory: Streamlit may be launched
# from a different location on Windows, Docker or an ECS service manager.
# Windows Defender's Controlled Folder Access can block writes to Desktop, so
# local Windows runs use the user's LocalAppData by default.  Docker/ECS uses
# the project data directory (or the explicit ZHIKE_DATABASE_PATH override).
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _database_candidates() -> list[Path]:
    configured = os.getenv("ZHIKE_DATABASE_PATH")
    if configured:
        # An explicit deployment path is intentional; do not silently store
        # production data somewhere else when that mounted path is unavailable.
        return [Path(configured).expanduser()]

    if os.name == "nt":
        app_data = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return [
            app_data / "ZhiKeAI" / "zhike.db",
            Path(tempfile.gettempdir()) / "ZhiKeAI" / "zhike.db",
        ]
    return [PROJECT_ROOT / "data" / "zhike.db"]


def _resolve_database_path() -> Path:
    errors: list[str] = []
    for candidate in _database_candidates():
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            return candidate
        except OSError as exc:
            errors.append(f"{candidate.parent}: {exc}")
    raise RuntimeError("无法创建知客本地数据目录。" + "；".join(errors))


DATABASE_PATH = _resolve_database_path()
PBKDF2_ITERATIONS = 310_000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    """Create the W4 single-user/team-ready tables if they do not exist."""
    with _connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS business_goals (
                user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS customers (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                raw_note TEXT NOT NULL,
                industry TEXT,
                stage TEXT,
                priority TEXT,
                risk TEXT,
                status TEXT NOT NULL DEFAULT '待跟进',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_customers_user_updated
                ON customers(user_id, updated_at DESC);
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                report_json TEXT NOT NULL,
                trace_json TEXT NOT NULL,
                provider TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_reports_customer_created
                ON reports(customer_id, created_at DESC);
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                due_at TEXT,
                status TEXT NOT NULL DEFAULT '待办',
                source TEXT NOT NULL DEFAULT '人工创建',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_user_status
                ON tasks(user_id, status, updated_at DESC);
            CREATE TABLE IF NOT EXISTS feedback_events (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL,
                note TEXT NOT NULL,
                is_reverted INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                reverted_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_feedback_user_created
                ON feedback_events(user_id, created_at DESC);
            """
        )


def _password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        ).hex()
        return hmac.compare_digest(candidate, digest_hex)
    except (TypeError, ValueError):
        return False


def create_user(email: str, display_name: str, password: str) -> dict[str, str]:
    email = email.strip().lower()
    display_name = display_name.strip()
    if not email or "@" not in email:
        raise ValueError("请输入有效的邮箱地址。")
    if len(display_name) < 2:
        raise ValueError("姓名至少需要 2 个字符。")
    if len(password) < 8:
        raise ValueError("密码至少需要 8 位。")
    user = {"id": uuid4().hex, "email": email, "display_name": display_name}
    try:
        with _connection() as db:
            db.execute(
                "INSERT INTO users(id,email,display_name,password_hash,created_at) VALUES(?,?,?,?,?)",
                (user["id"], email, display_name, _password_hash(password), _now()),
            )
    except sqlite3.IntegrityError as exc:
        raise ValueError("该邮箱已注册，请直接登录。") from exc
    return user


def authenticate_user(email: str, password: str) -> dict[str, str] | None:
    with _connection() as db:
        row = db.execute(
            "SELECT id,email,display_name,password_hash FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
    if not row or not _verify_password(password, row["password_hash"]):
        return None
    return {"id": row["id"], "email": row["email"], "display_name": row["display_name"]}


def save_goal(user_id: str, payload: dict[str, Any]) -> None:
    with _connection() as db:
        db.execute(
            """INSERT INTO business_goals(user_id,payload,updated_at) VALUES(?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET payload=excluded.payload,updated_at=excluded.updated_at""",
            (user_id, json.dumps(payload, ensure_ascii=False), _now()),
        )


def load_goal(user_id: str) -> dict[str, Any] | None:
    with _connection() as db:
        row = db.execute("SELECT payload FROM business_goals WHERE user_id = ?", (user_id,)).fetchone()
    return json.loads(row["payload"]) if row else None


def create_customer(user_id: str, name: str, raw_note: str, metadata: dict[str, str]) -> str:
    customer_id = uuid4().hex
    now = _now()
    with _connection() as db:
        db.execute(
            """INSERT INTO customers(id,user_id,name,raw_note,industry,stage,priority,risk,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (customer_id, user_id, name, raw_note, metadata.get("industry"), metadata.get("stage"),
             metadata.get("priority"), metadata.get("risk"), now, now),
        )
    return customer_id


def save_report(user_id: str, customer_id: str, report: dict[str, Any], trace: list[dict[str, Any]], provider: str) -> str:
    report_id = uuid4().hex
    with _connection() as db:
        db.execute(
            "INSERT INTO reports(id,customer_id,user_id,report_json,trace_json,provider,created_at) VALUES(?,?,?,?,?,?,?)",
            (report_id, customer_id, user_id, json.dumps(report, ensure_ascii=False),
             json.dumps(trace, ensure_ascii=False), provider, _now()),
        )
        db.execute("UPDATE customers SET updated_at = ? WHERE id = ? AND user_id = ?", (_now(), customer_id, user_id))
    return report_id


def list_customers(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    with _connection() as db:
        rows = db.execute(
            """SELECT id,name,industry,stage,priority,risk,status,updated_at FROM customers
               WHERE user_id=? ORDER BY updated_at DESC LIMIT ?""", (user_id, limit)
        ).fetchall()
    return [dict(row) for row in rows]


def get_customer(user_id: str, customer_id: str) -> dict[str, Any] | None:
    """Return one owned customer, its newest report and feedback history."""
    with _connection() as db:
        customer = db.execute(
            "SELECT * FROM customers WHERE id=? AND user_id=?", (customer_id, user_id)
        ).fetchone()
        if not customer:
            return None
        report = db.execute(
            "SELECT report_json,trace_json,provider,created_at FROM reports WHERE customer_id=? AND user_id=? ORDER BY created_at DESC LIMIT 1",
            (customer_id, user_id),
        ).fetchone()
        feedback = db.execute(
            "SELECT id,event_type,note,is_reverted,created_at,reverted_at FROM feedback_events WHERE customer_id=? AND user_id=? ORDER BY created_at DESC",
            (customer_id, user_id),
        ).fetchall()
    payload = dict(customer)
    payload["report"] = json.loads(report["report_json"]) if report else None
    payload["trace"] = json.loads(report["trace_json"]) if report else []
    payload["provider"] = report["provider"] if report else None
    payload["feedback"] = [dict(item) for item in feedback]
    return payload


def dashboard_snapshot(user_id: str) -> dict[str, Any]:
    """Compute auditable dashboard counts solely from persisted human events."""
    customers = list_customers(user_id)
    with _connection() as db:
        rows = db.execute(
            """SELECT event_type,COUNT(*) AS total FROM feedback_events
               WHERE user_id=? AND is_reverted=0 GROUP BY event_type""",
            (user_id,),
        ).fetchall()
    counts = {row["event_type"]: int(row["total"]) for row in rows}
    return {
        "customer_count": len(customers),
        "qualified_customers": counts.get("need_confirmed", 0),
        "effective_communications": counts.get("effective_communication", 0),
        "solution_meetings": counts.get("solution_meeting", 0),
        "priority_advanced": counts.get("priority_advanced", 0),
        "customers": customers,
        "tasks": list_tasks(user_id),
    }


def create_task(user_id: str, customer_id: str, title: str, due_at: str = "", source: str = "AI 建议") -> str:
    if not title.strip():
        raise ValueError("任务内容不能为空。")
    task_id = uuid4().hex
    now = _now()
    with _connection() as db:
        db.execute(
            "INSERT INTO tasks(id,customer_id,user_id,title,due_at,source,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (task_id, customer_id, user_id, title.strip(), due_at.strip() or None, source, now, now),
        )
    return task_id


def list_tasks(user_id: str, include_done: bool = False) -> list[dict[str, Any]]:
    clause = "" if include_done else "AND t.status != '已完成'"
    with _connection() as db:
        rows = db.execute(
            f"""SELECT t.id,t.title,t.due_at,t.status,t.source,c.name AS customer_name,c.priority,c.risk
                 FROM tasks t JOIN customers c ON c.id=t.customer_id
                 WHERE t.user_id=? {clause} ORDER BY CASE c.priority WHEN '高' THEN 0 WHEN '中' THEN 1 ELSE 2 END, t.updated_at DESC""",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def update_task_status(user_id: str, task_id: str, status: str) -> None:
    if status not in {"待办", "已完成", "已延期", "已取消"}:
        raise ValueError("未知任务状态。")
    with _connection() as db:
        cursor = db.execute(
            "UPDATE tasks SET status=?,updated_at=? WHERE id=? AND user_id=?", (status, _now(), task_id, user_id)
        )
    if cursor.rowcount != 1:
        raise ValueError("未找到该任务。")


def record_feedback_event(user_id: str, customer_id: str, event_type: str, note: str = "") -> str:
    event_id = uuid4().hex
    with _connection() as db:
        db.execute(
            "INSERT INTO feedback_events(id,customer_id,user_id,event_type,note,created_at) VALUES(?,?,?,?,?,?)",
            (event_id, customer_id, user_id, event_type, note.strip(), _now()),
        )
    return event_id


def revert_feedback_event(user_id: str, event_id: str) -> None:
    with _connection() as db:
        cursor = db.execute(
            "UPDATE feedback_events SET is_reverted=1,reverted_at=? WHERE id=? AND user_id=? AND is_reverted=0",
            (_now(), event_id, user_id),
        )
    if cursor.rowcount != 1:
        raise ValueError("该反馈不存在或已撤销。")
