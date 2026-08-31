from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Any
from uuid import uuid4

from personal_ai_os_core import MemoryStatus

from .db import Database
from .project_state import ProjectStateService
from .project_workflow import ProjectWorkflowService
from .runtime import Runtime
from .schemas import ChatRequest, ToolActionPreviewRequest


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return (value or _now()).isoformat()


def _token_estimate(*values: str) -> int:
    return max(1, ceil(sum(len(value) for value in values) / 4))


def _arguments_digest(arguments: dict[str, Any]) -> str:
    encoded = json.dumps(arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _period_start(period: str, now: datetime | None = None) -> datetime:
    value = now or _now()
    if period == "daily":
        return value.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "weekly":
        start = value.replace(hour=0, minute=0, second=0, microsecond=0)
        return start - timedelta(days=start.weekday())
    if period == "monthly":
        return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    raise ValueError(f"Unsupported budget period: {period}")


class GovernanceService:
    """Persisted, tenant-scoped product-control receipts without secret values."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def reviewed_memories(self, project_id: str) -> list[dict[str, Any]]:
        return [
            item.model_dump(mode="json")
            for item in self.database.list_memories(MemoryStatus.ACTIVE.value)
            if item.project_id in {None, project_id}
        ][:20]

    def send_scope_preview(self, runtime: Runtime, request: ChatRequest) -> dict[str, Any]:
        project = runtime.projects.get(request.project_id)
        if request.conversation_id:
            conversation = runtime.database.get_conversation(request.conversation_id)
            if conversation is None:
                raise ValueError("Conversation not found")
            if conversation.project_id != request.project_id:
                raise ValueError("A conversation cannot change project context")
        state = ProjectStateService(
            runtime.database,
            data_dir=runtime.settings.data_dir,
            tenant_id=runtime.settings.tenant_id,
        ).context_json(request.project_id)
        workflow = ProjectWorkflowService(
            runtime.database,
            data_dir=runtime.settings.data_dir,
            tenant_id=runtime.settings.tenant_id,
        ).context_json(request.project_id)
        history = (
            runtime.database.list_messages(request.conversation_id)
            if request.conversation_id and runtime.database.get_conversation(request.conversation_id)
            else []
        )
        memories = self.reviewed_memories(request.project_id)
        tool_availability = []
        if request.tool:
            tool_availability.append(
                {
                    "connector_id": request.tool.connector_id or "local-reference",
                    "tool": request.tool.name,
                    "confirmation_required": bool(request.tool.connector_id),
                }
            )
        categories = ["user_message", "project_metadata", "project_persistent_state", "project_workflow"]
        if history:
            categories.append("conversation_history")
        if memories:
            categories.append("reviewed_memory")
        approximate_tokens = _token_estimate(
            request.content,
            json.dumps(project.context(), ensure_ascii=False),
            state,
            workflow,
            "".join(item.content for item in history),
            "".join(str(item["text"]) for item in memories),
        )
        return {
            "project_id": request.project_id,
            "provider": request.provider,
            "model": request.model,
            "selected_files": [],
            "reviewed_memory_ids": [item["id"] for item in memories],
            "tool_availability": tool_availability,
            "conversation_context": "existing" if history else "new",
            "context_categories": categories,
            "approximate_context_tokens": approximate_tokens,
            "context_precision": "ESTIMATED",
            "secrets_included": False,
            "hidden_reasoning_included": False,
        }

    def save_send_scope(
        self,
        scope: dict[str, Any],
        *,
        conversation_id: str | None,
        status: str,
    ) -> dict[str, Any]:
        receipt = {"id": str(uuid4()), "conversation_id": conversation_id, "status": status, **scope}
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO send_scope_receipts(id, tenant_id, conversation_id, project_id, provider, model, "
                "selected_files_json, reviewed_memory_ids_json, tool_availability_json, context_categories_json, "
                "approximate_context_tokens, context_precision, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    receipt["id"], self.database.tenant_id, conversation_id, scope["project_id"],
                    scope["provider"], scope["model"], json.dumps(scope["selected_files"]),
                    json.dumps(scope["reviewed_memory_ids"]), json.dumps(scope["tool_availability"]),
                    json.dumps(scope["context_categories"]), scope["approximate_context_tokens"],
                    scope["context_precision"], status, _iso(),
                ),
            )
        return receipt

    def get_send_scope(self, receipt_id: str) -> dict[str, Any] | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM send_scope_receipts WHERE id = ? AND tenant_id = ?",
                (receipt_id, self.database.tenant_id),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"], "conversation_id": row["conversation_id"], "project_id": row["project_id"],
            "provider": row["provider"], "model": row["model"],
            "selected_files": json.loads(row["selected_files_json"]),
            "reviewed_memory_ids": json.loads(row["reviewed_memory_ids_json"]),
            "tool_availability": json.loads(row["tool_availability_json"]),
            "context_categories": json.loads(row["context_categories_json"]),
            "approximate_context_tokens": row["approximate_context_tokens"],
            "context_precision": row["context_precision"], "status": row["status"], "created_at": row["created_at"],
            "secrets_included": False, "hidden_reasoning_included": False,
        }

    def create_execution_run(self, *, conversation_id: str, project_id: str, provider: str, model: str) -> str:
        run_id = str(uuid4())
        now = _iso()
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO execution_runs(id, tenant_id, conversation_id, project_id, provider, model, status, "
                "retry_status, side_effect_status, detail_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, self.database.tenant_id, conversation_id, project_id, provider, model, "running", "retry_safe", "not_started", "{}", now, now),
            )
        return run_id

    def update_execution_run(self, run_id: str, *, status: str, retry_status: str, side_effect_status: str, detail: dict[str, Any] | None = None) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE execution_runs SET status = ?, retry_status = ?, side_effect_status = ?, detail_json = ?, updated_at = ? "
                "WHERE id = ? AND tenant_id = ?",
                (status, retry_status, side_effect_status, json.dumps(detail or {}), _iso(), run_id, self.database.tenant_id),
            )

    def get_execution_run(self, run_id: str) -> dict[str, Any] | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM execution_runs WHERE id = ? AND tenant_id = ?", (run_id, self.database.tenant_id)
            ).fetchone()
        if not row:
            return None
        item = dict(row)
        item.pop("tenant_id", None)
        item["detail"] = json.loads(item.pop("detail_json"))
        return item

    def list_execution_runs(self, conversation_id: str) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM execution_runs WHERE conversation_id = ? AND tenant_id = ? ORDER BY created_at DESC",
                (conversation_id, self.database.tenant_id),
            ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item.pop("tenant_id", None)
            item["detail"] = json.loads(item.pop("detail_json"))
            items.append(item)
        return items

    def record_usage(self, *, conversation_id: str, project_id: str, provider: str, model: str, input_tokens: int, output_tokens: int | None, status: str, latency_ms: int) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO usage_ledger(id, tenant_id, conversation_id, project_id, provider, model, status, input_tokens, output_tokens, token_precision, cost_usd, cost_precision, latency_ms, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid4()), self.database.tenant_id, conversation_id, project_id, provider, model, status,
                 input_tokens, output_tokens, "ESTIMATED", None, "UNKNOWN", latency_ms, _iso()),
            )

    def _scope_matches(self, scope_type: str, project_id: str) -> tuple[str, tuple[object, ...]]:
        if scope_type == "tenant":
            return "", ()
        return " AND project_id = ?", (project_id,)

    def _spent_tokens(self, connection, scope_type: str, project_id: str) -> int:
        constraint, params = self._scope_matches(scope_type, project_id)
        row = connection.execute(
            "SELECT COALESCE(SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)), 0) AS total "
            "FROM usage_ledger WHERE tenant_id = ?" + constraint,
            (self.database.tenant_id, *params),
        ).fetchone()
        return int(row["total"])

    def _reserved_tokens(self, connection, scope_type: str, project_id: str, *, now: str) -> int:
        constraint, params = self._scope_matches(scope_type, project_id)
        row = connection.execute(
            "SELECT COALESCE(SUM(reserved_tokens), 0) AS total FROM budget_reservations "
            "WHERE tenant_id = ? AND status IN ('active', 'unknown') AND expires_at > ?" + constraint,
            (self.database.tenant_id, now, *params),
        ).fetchone()
        return int(row["total"])

    def _budget_rows(self, project_id: str, connection=None) -> list[Any]:
        query = (
            "SELECT * FROM budget_policies WHERE tenant_id = ? "
            "AND ((scope_type = 'tenant' AND scope_id = ?) OR (scope_type = 'project' AND scope_id = ?))"
        )
        params = (self.database.tenant_id, self.database.tenant_id, project_id)
        if connection is not None:
            return connection.execute(query, params).fetchall()
        with self.database.connect() as owned_connection:
            return owned_connection.execute(query, params).fetchall()

    def budget_status(self, project_id: str, *, upcoming_tokens: int = 0) -> dict[str, Any]:
        policies = []
        blocked = False
        now = _iso()
        with self.database.connect() as connection:
            for row in self._budget_rows(project_id, connection):
                start = _period_start(row["period"]).isoformat()
                constraint, params = self._scope_matches(row["scope_type"], project_id)
                spent = connection.execute(
                    "SELECT COALESCE(SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)), 0) AS total FROM usage_ledger "
                    "WHERE tenant_id = ? AND created_at >= ?" + constraint,
                    (self.database.tenant_id, start, *params),
                ).fetchone()["total"]
                reserved = self._reserved_tokens(connection, row["scope_type"], project_id, now=now)
                projected = int(spent) + reserved + upcoming_tokens
                policy_blocked = bool(row["hard_limit"] and projected >= row["limit_tokens"])
                blocked = blocked or policy_blocked
                policies.append({
                    "scope_type": row["scope_type"], "scope_id": row["scope_id"], "period": row["period"],
                    "limit_tokens": row["limit_tokens"], "warn_percent": row["warn_percent"], "hard_limit": bool(row["hard_limit"]),
                    "used_tokens": int(spent), "reserved_tokens": reserved, "projected_tokens": projected,
                    "warn": projected * 100 >= row["limit_tokens"] * row["warn_percent"], "blocked": policy_blocked,
                    "token_precision": "ESTIMATED",
                })
        return {"project_id": project_id, "blocked": blocked, "policies": policies}

    def reserve_budget(self, project_id: str, *, tokens: int, reason: str) -> dict[str, Any]:
        """Atomically reserve estimated usage so concurrent preflights cannot both exceed a hard limit."""
        tokens = max(1, int(tokens))
        now = _iso()
        reservation_id = str(uuid4())
        policies: list[dict[str, Any]] = []
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            for row in self._budget_rows(project_id, connection):
                start = _period_start(row["period"]).isoformat()
                constraint, params = self._scope_matches(row["scope_type"], project_id)
                spent = int(connection.execute(
                    "SELECT COALESCE(SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)), 0) AS total "
                    "FROM usage_ledger WHERE tenant_id = ? AND created_at >= ?" + constraint,
                    (self.database.tenant_id, start, *params),
                ).fetchone()["total"])
                reserved = self._reserved_tokens(connection, row["scope_type"], project_id, now=now)
                projected = spent + reserved + tokens
                blocked = bool(row["hard_limit"] and projected >= row["limit_tokens"])
                policies.append({"period": row["period"], "scope_type": row["scope_type"], "projected_tokens": projected, "blocked": blocked})
            if any(item["blocked"] for item in policies):
                return {"blocked": True, "reservation_id": None, "policies": policies}
            if policies:
                connection.execute(
                    "INSERT INTO budget_reservations(id, tenant_id, project_id, reserved_tokens, status, reason, expires_at, created_at) "
                    "VALUES (?, ?, ?, ?, 'active', ?, ?, ?)",
                    (reservation_id, self.database.tenant_id, project_id, tokens, reason, _iso(_now() + timedelta(minutes=15)), now),
                )
        return {"blocked": False, "reservation_id": reservation_id if policies else None, "policies": policies}

    def attach_budget_reservation(self, reservation_id: str | None, execution_id: str) -> None:
        if not reservation_id:
            return
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE budget_reservations SET execution_id = ? WHERE id = ? AND tenant_id = ? AND status = 'active'",
                (execution_id, reservation_id, self.database.tenant_id),
            )

    def settle_budget_reservation(self, reservation_id: str | None, *, status: str) -> None:
        if not reservation_id:
            return
        if status not in {"committed", "released", "unknown"}:
            raise ValueError("Unsupported reservation settlement status")
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE budget_reservations SET status = ?, settled_at = ? "
                "WHERE id = ? AND tenant_id = ? AND status = 'active'",
                (status, _iso(), reservation_id, self.database.tenant_id),
            )

    def set_budget_policy(self, values: dict[str, Any]) -> dict[str, Any]:
        if values["scope_type"] == "tenant" and values["scope_id"] != self.database.tenant_id:
            raise ValueError("Tenant budgets must use the current tenant scope")
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO budget_policies(tenant_id, scope_type, scope_id, period, limit_tokens, warn_percent, hard_limit, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(tenant_id, scope_type, scope_id, period) DO UPDATE SET limit_tokens = excluded.limit_tokens, warn_percent = excluded.warn_percent, hard_limit = excluded.hard_limit, updated_at = excluded.updated_at",
                (self.database.tenant_id, values["scope_type"], values["scope_id"], values["period"], values["limit_tokens"], values["warn_percent"], int(values["hard_limit"]), _iso()),
            )
        return self.budget_status(values["scope_id"] if values["scope_type"] == "project" else "general")

    def usage_summary(self, project_id: str | None = None) -> dict[str, Any]:
        query = "SELECT provider, model, status, token_precision, cost_precision, COUNT(*) AS requests, COALESCE(SUM(input_tokens), 0) AS input_tokens, COALESCE(SUM(output_tokens), 0) AS output_tokens, COALESCE(SUM(latency_ms), 0) AS latency_ms FROM usage_ledger WHERE tenant_id = ?"
        params: list[Any] = [self.database.tenant_id]
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        query += " GROUP BY provider, model, status, token_precision, cost_precision ORDER BY provider, model"
        with self.database.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return {"items": [dict(row) | {"actual_provider_cost": None, "cost_usd": None} for row in rows]}

    def routing_settings(self) -> dict[str, Any]:
        policy = self.database.get_setting("routing_policy") or "STRICT_PROVIDER"
        provider = self.database.get_setting("fallback_provider")
        model = self.database.get_setting("fallback_model")
        return {
            "policy": policy,
            "fallback_provider": provider,
            "fallback_model": model,
            "provider_session_copied": False,
        }

    def set_routing_settings(self, values: dict[str, Any]) -> dict[str, Any]:
        self.database.set_setting("routing_policy", values["policy"])
        self.database.set_setting("fallback_provider", values.get("fallback_provider") or "")
        self.database.set_setting("fallback_model", values.get("fallback_model") or "")
        return self.routing_settings()

    def eligible_fallback(
        self,
        runtime: Runtime,
        *,
        provider_id: str,
        request_has_tool: bool,
        explicit_confirmation: bool,
    ) -> tuple[str, str, str] | None:
        settings = self.routing_settings()
        if request_has_tool or settings["policy"] == "STRICT_PROVIDER":
            return None
        if settings["policy"] == "ASK_BEFORE_FALLBACK" and not explicit_confirmation:
            return None
        fallback_id = settings["fallback_provider"]
        fallback_model = settings["fallback_model"]
        if not fallback_id or not fallback_model or fallback_id == provider_id:
            return None
        try:
            fallback = runtime.providers.get(fallback_id)
        except KeyError:
            return None
        if not fallback.configured or fallback_model not in fallback.models:
            return None
        return str(fallback_id), str(fallback_model), str(settings["policy"])

    def preview_tool_action(self, runtime: Runtime, payload: ToolActionPreviewRequest) -> dict[str, Any]:
        connector = runtime.external_mcp.get(payload.connector_id)
        if not connector.enabled or payload.tool_name not in connector.allowed_tools:
            raise ValueError("Tool is not enabled and explicitly allowlisted for this connector")
        now = _now()
        preview = {
            "project_id": payload.project_id, "connector_id": payload.connector_id, "tool_name": payload.tool_name,
            "arguments": payload.arguments, "risk": "external_mutation_or_unknown", "requires_confirmation": True,
            "status": "previewed", "expires_at": _iso(now + timedelta(minutes=10)),
        }
        preview_id = str(uuid4())
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO tool_action_confirmations(id, tenant_id, actor_id, project_id, connector_id, tool_name, arguments_digest, preview_json, status, expires_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (preview_id, self.database.tenant_id, self.database.actor_id, payload.project_id, payload.connector_id, payload.tool_name,
                 _arguments_digest(payload.arguments), json.dumps(preview), "previewed", preview["expires_at"], _iso(now)),
            )
        return {"id": preview_id, **preview}

    def confirm_tool_action(self, confirmation_id: str) -> dict[str, Any] | None:
        now = _iso()
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM tool_action_confirmations WHERE id = ? AND tenant_id = ? AND actor_id = ?", (confirmation_id, self.database.tenant_id, self.database.actor_id)
            ).fetchone()
            if not row or row["status"] != "previewed" or row["expires_at"] <= now:
                return None
            updated = connection.execute(
                "UPDATE tool_action_confirmations SET status = 'confirmed', confirmed_at = ? "
                "WHERE id = ? AND tenant_id = ? AND actor_id = ? AND status = 'previewed' AND expires_at > ?",
                (now, confirmation_id, self.database.tenant_id, self.database.actor_id, now),
            )
            if updated.rowcount != 1:
                return None
        preview = json.loads(row["preview_json"])
        return {"id": confirmation_id, **preview, "status": "confirmed"}

    def consume_tool_confirmation(self, *, confirmation_id: str | None, project_id: str, connector_id: str | None, tool_name: str, arguments: dict[str, Any]) -> bool:
        if not connector_id:
            return True
        if not confirmation_id:
            return False
        now = _iso()
        with self.database.connect() as connection:
            updated = connection.execute(
                "UPDATE tool_action_confirmations SET status = 'consumed', consumed_at = ? "
                "WHERE id = ? AND tenant_id = ? AND actor_id = ? AND project_id = ? AND connector_id = ? "
                "AND tool_name = ? AND arguments_digest = ? AND status = 'confirmed' AND expires_at > ?",
                (
                    now, confirmation_id, self.database.tenant_id, self.database.actor_id, project_id,
                    connector_id, tool_name, _arguments_digest(arguments), now,
                ),
            )
        return updated.rowcount == 1
