from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Iterator

from personal_ai_os_core import ProjectMetadata, ProjectView


BEIJING = timezone(timedelta(hours=8), "Asia/Shanghai")
MODEL_VERSION = "p5-gpt-10xthink-v1"
WORKFLOW_VERSION = "P5_POST_DRAW_2222_NEXT_DAY_V1"
OBSERVATION_ARM = "UNQUALIFIED_OBSERVATION_ARM"
MONEY_STAKED_CNY = 0
LIVE_BETTING_ALLOWED = False
RULE_WEIGHT_MIN_OBSERVATIONS = 10
RULE_PAUSE_MIN_OBSERVATIONS = 20
RULE_PAUSE_POSITIVE_RATE = 0.20
ISSUE_PATTERN = re.compile(r"^[0-9]{5,12}$")
NUMBER_PATTERN = re.compile(r"^[0-9]{5}$")

RULES = (
    ("digit_balance", "Digit sum balance", 0.23),
    ("digit_diversity", "Digit diversity", 0.22),
    ("adjacency_control", "Adjacent repeat control", 0.18),
    ("odd_even_balance", "Odd/even balance", 0.17),
    ("deterministic_signal", "Deterministic trend signal", 0.20),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _research_boundary() -> dict[str, Any]:
    return {
        "observation_arm": OBSERVATION_ARM,
        "money_staked_cny": MONEY_STAKED_CNY,
        "live_betting_allowed": LIVE_BETTING_ALLOWED,
        "top10_role": "diagnostic_verification_prefix",
        "top5_role": "diagnostic_verification_prefix",
    }


def _validate_issue(value: str, field: str = "issue") -> str:
    if not ISSUE_PATTERN.fullmatch(value):
        raise ValueError(f"{field} must contain 5 to 12 digits")
    return value


def _validate_number(value: str, field: str = "number") -> str:
    if not NUMBER_PATTERN.fullmatch(value):
        raise ValueError(f"{field} must contain exactly 5 digits")
    return value


def _row_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    for key in ("feature_scores", "filters_triggered", "metrics", "rule_updates", "payload"):
        json_key = f"{key}_json"
        if json_key in item:
            raw = item.pop(json_key)
            item[key] = json.loads(raw) if raw is not None else None
    for key in ("survived_final_filter", "is_top10", "is_top5", "active"):
        if key in item:
            item[key] = bool(item[key])
    return item


class P5Store:
    """Plugin-owned persistence. It never changes Personal AI OS core tables."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._migration_lock = Lock()
        self._migrated = False

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.migrate()
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def migrate(self) -> None:
        if self._migrated:
            return
        with self._migration_lock:
            if self._migrated:
                return
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path, timeout=30)
            try:
                connection.executescript(
                    """
                    PRAGMA journal_mode = WAL;
                    CREATE TABLE IF NOT EXISTS p5_issues (
                        issue TEXT PRIMARY KEY,
                        draw_date TEXT,
                        status TEXT NOT NULL,
                        official_result TEXT,
                        result_confirmed_at TEXT,
                        retry_at TEXT,
                        model_version TEXT,
                        workflow_version TEXT NOT NULL,
                        generated_at TEXT,
                        locked_at TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS p5_candidates (
                        issue TEXT NOT NULL,
                        number TEXT NOT NULL,
                        generated_order INTEGER NOT NULL,
                        raw_score REAL NOT NULL,
                        adjusted_score REAL NOT NULL,
                        feature_scores_json TEXT NOT NULL,
                        filters_triggered_json TEXT NOT NULL,
                        elimination_reason TEXT,
                        survived_final_filter INTEGER NOT NULL,
                        final_rank INTEGER NOT NULL,
                        is_top10 INTEGER NOT NULL,
                        is_top5 INTEGER NOT NULL,
                        model_version TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        PRIMARY KEY (issue, number),
                        UNIQUE (issue, generated_order),
                        UNIQUE (issue, final_rank),
                        FOREIGN KEY (issue) REFERENCES p5_issues(issue) ON DELETE RESTRICT
                    );
                    CREATE INDEX IF NOT EXISTS idx_p5_candidates_rank
                        ON p5_candidates(issue, final_rank);
                    CREATE TABLE IF NOT EXISTS p5_reviews (
                        issue TEXT PRIMARY KEY,
                        official_result TEXT NOT NULL,
                        metrics_json TEXT NOT NULL,
                        rule_updates_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (issue) REFERENCES p5_issues(issue) ON DELETE RESTRICT
                    );
                    CREATE TABLE IF NOT EXISTS p5_rules (
                        rule_id TEXT PRIMARY KEY,
                        label TEXT NOT NULL,
                        weight REAL NOT NULL,
                        positive_count INTEGER NOT NULL DEFAULT 0,
                        negative_count INTEGER NOT NULL DEFAULT 0,
                        active INTEGER NOT NULL DEFAULT 1,
                        updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS p5_audit (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        issue TEXT,
                        action TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    """
                )
                now = _utc_now()
                connection.executemany(
                    """
                    INSERT OR IGNORE INTO p5_rules
                        (rule_id, label, weight, positive_count, negative_count, active, updated_at)
                    VALUES (?, ?, ?, 0, 0, 1, ?)
                    """,
                    [(rule_id, label, weight, now) for rule_id, label, weight in RULES],
                )
                connection.commit()
            finally:
                connection.close()
            self._migrated = True

    def _audit(
        self,
        connection: sqlite3.Connection,
        action: str,
        issue: str | None,
        payload: dict[str, Any],
        created_at: str,
    ) -> None:
        connection.execute(
            "INSERT INTO p5_audit(issue, action, payload_json, created_at) VALUES (?, ?, ?, ?)",
            (issue, action, json.dumps(payload, ensure_ascii=False, sort_keys=True), created_at),
        )

    def _record_waiting(
        self,
        issue: str,
        draw_date: str | None,
        status: str,
        retry_at: datetime,
        now: datetime,
    ) -> dict[str, Any]:
        created_at = now.astimezone(timezone.utc).isoformat()
        retry = retry_at.astimezone(BEIJING).isoformat()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO p5_issues(
                    issue, draw_date, status, retry_at, workflow_version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(issue) DO UPDATE SET
                    draw_date = COALESCE(excluded.draw_date, p5_issues.draw_date),
                    status = excluded.status,
                    retry_at = excluded.retry_at,
                    updated_at = excluded.updated_at
                """,
                (issue, draw_date, status, retry, WORKFLOW_VERSION, created_at, created_at),
            )
            self._audit(
                connection,
                "result.waiting",
                issue,
                {"status": status, "retry_at": retry, "timezone": "Asia/Shanghai"},
                created_at,
            )
        return {
            "status": status,
            "issue": issue,
            "retry_at": retry,
            "workflow_version": WORKFLOW_VERSION,
            "result_confirmed": False,
            **_research_boundary(),
        }

    def run_daily(
        self,
        *,
        result_issue: str,
        next_issue: str,
        next_draw_date: str,
        official_result: str | None,
        result_confirmed: bool,
        now_beijing: datetime | None = None,
    ) -> dict[str, Any]:
        result_issue = _validate_issue(result_issue, "result_issue")
        next_issue = _validate_issue(next_issue, "next_issue")
        if result_issue == next_issue:
            raise ValueError("next_issue must differ from result_issue")
        try:
            date.fromisoformat(next_draw_date)
        except ValueError as exc:
            raise ValueError("next_draw_date must use YYYY-MM-DD") from exc

        now = now_beijing or datetime.now(BEIJING)
        if now.tzinfo is None:
            now = now.replace(tzinfo=BEIJING)
        else:
            now = now.astimezone(BEIJING)
        gate = datetime.combine(now.date(), time(22, 22), tzinfo=BEIJING)
        if now < gate:
            return self._record_waiting(
                result_issue, None, "waiting_for_2222", gate, now
            )
        if not result_confirmed or official_result is None:
            return self._record_waiting(
                result_issue, None, "waiting_for_result", now + timedelta(minutes=10), now
            )
        official_result = _validate_number(official_result, "official_result")

        created_at = now.astimezone(timezone.utc).isoformat()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing_result = connection.execute(
                "SELECT official_result FROM p5_issues WHERE issue = ?", (result_issue,)
            ).fetchone()
            if (
                existing_result is not None
                and existing_result["official_result"] is not None
                and existing_result["official_result"] != official_result
            ):
                raise RuntimeError(
                    f"Official result conflict for {result_issue}: existing value is immutable"
                )
            connection.execute(
                """
                INSERT INTO p5_issues(
                    issue, status, official_result, result_confirmed_at,
                    workflow_version, created_at, updated_at
                ) VALUES (?, 'reviewed', ?, ?, ?, ?, ?)
                ON CONFLICT(issue) DO UPDATE SET
                    status = 'reviewed', official_result = excluded.official_result,
                    result_confirmed_at = excluded.result_confirmed_at,
                    retry_at = NULL, updated_at = excluded.updated_at
                """,
                (
                    result_issue,
                    official_result,
                    created_at,
                    WORKFLOW_VERSION,
                    created_at,
                    created_at,
                ),
            )
            review = self._review(connection, result_issue, official_result, created_at)
            existing_count = connection.execute(
                "SELECT COUNT(*) AS count FROM p5_candidates WHERE issue = ?", (next_issue,)
            ).fetchone()["count"]
            next_state = connection.execute(
                "SELECT * FROM p5_issues WHERE issue = ?", (next_issue,)
            ).fetchone()
            if existing_count not in (0, 10_000):
                raise RuntimeError(
                    f"Refusing partial candidate set for {next_issue}: {existing_count} rows"
                )
            if existing_count == 0 and next_state is not None:
                raise RuntimeError(
                    f"Refusing to repurpose existing issue state for {next_issue}"
                )
            if existing_count == 10_000:
                if (
                    next_state is None
                    or next_state["status"] != "locked"
                    or next_state["draw_date"] != next_draw_date
                    or next_state["model_version"] != MODEL_VERSION
                    or next_state["workflow_version"] != WORKFLOW_VERSION
                ):
                    raise RuntimeError(
                        f"Immutable lock metadata conflict for {next_issue}"
                    )
                candidate_versions = connection.execute(
                    """
                    SELECT COUNT(DISTINCT model_version) AS version_count,
                        MIN(model_version) AS model_version
                    FROM p5_candidates WHERE issue = ?
                    """,
                    (next_issue,),
                ).fetchone()
                if (
                    candidate_versions["version_count"] != 1
                    or candidate_versions["model_version"] != MODEL_VERSION
                ):
                    raise RuntimeError(
                        f"Immutable candidate model conflict for {next_issue}"
                    )
            if existing_count == 0:
                candidates = self._generate_candidates(connection, next_issue, created_at)
                connection.execute(
                    """
                    INSERT INTO p5_issues(
                        issue, draw_date, status, model_version, workflow_version,
                        generated_at, locked_at, created_at, updated_at
                    ) VALUES (?, ?, 'locked', ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(issue) DO UPDATE SET
                        draw_date = excluded.draw_date, status = 'locked',
                        model_version = excluded.model_version,
                        generated_at = excluded.generated_at, locked_at = excluded.locked_at,
                        updated_at = excluded.updated_at
                    """,
                    (
                        next_issue,
                        next_draw_date,
                        MODEL_VERSION,
                        WORKFLOW_VERSION,
                        created_at,
                        created_at,
                        created_at,
                        created_at,
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO p5_candidates(
                        issue, number, generated_order, raw_score, adjusted_score,
                        feature_scores_json, filters_triggered_json, elimination_reason,
                        survived_final_filter, final_rank, is_top10, is_top5,
                        model_version, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    candidates,
                )
                persisted = connection.execute(
                    "SELECT COUNT(*) AS count FROM p5_candidates WHERE issue = ?", (next_issue,)
                ).fetchone()["count"]
                if persisted != 10_000:
                    raise RuntimeError(
                        f"Candidate lock requires exactly 10000 rows; got {persisted}"
                    )
                self._audit(
                    connection,
                    "forecast.locked",
                    next_issue,
                    {
                        "candidate_count": persisted,
                        "model_version": MODEL_VERSION,
                        "execution_path": "gpt/chatgpt",
                        "top10_count": 10,
                        "top5_count": 5,
                        "paper_only": True,
                        **_research_boundary(),
                    },
                    created_at,
                )
            else:
                persisted = existing_count
                self._audit(
                    connection,
                    "forecast.reused",
                    next_issue,
                    {
                        "candidate_count": persisted,
                        "reason": "immutable_existing_lock",
                        **_research_boundary(),
                    },
                    created_at,
                )
            top = connection.execute(
                """
                SELECT number, final_rank, adjusted_score, is_top10, is_top5
                FROM p5_candidates WHERE issue = ? AND final_rank <= 10 ORDER BY final_rank
                """,
                (next_issue,),
            ).fetchall()
        return {
            "status": "locked",
            "result_issue": result_issue,
            "next_issue": next_issue,
            "candidate_count": persisted,
            "review": review,
            "top10": [_row_dict(row) for row in top],
            "top5": [_row_dict(row) for row in top[:5]],
            "model_version": MODEL_VERSION,
            "workflow_version": WORKFLOW_VERSION,
            "execution_path": "gpt/chatgpt",
            "codex_invoked": False,
            "paper_only": True,
            **_research_boundary(),
        }

    def _review(
        self,
        connection: sqlite3.Connection,
        issue: str,
        result: str,
        created_at: str,
    ) -> dict[str, Any]:
        previous = connection.execute(
            """
            SELECT official_result, metrics_json, rule_updates_json
            FROM p5_reviews WHERE issue = ?
            """,
            (issue,),
        ).fetchone()
        if previous is not None:
            if previous["official_result"] != result:
                raise RuntimeError(
                    f"Review result conflict for {issue}: existing value is immutable"
                )
            return {
                "issue": issue,
                "official_result": result,
                "metrics": json.loads(previous["metrics_json"]),
                "rule_updates": json.loads(previous["rule_updates_json"]),
                "reused": True,
            }
        candidate = connection.execute(
            """
            SELECT final_rank, is_top10, is_top5, feature_scores_json
            FROM p5_candidates WHERE issue = ? AND number = ?
            """,
            (issue, result),
        ).fetchone()
        candidate_count = connection.execute(
            "SELECT COUNT(*) AS count FROM p5_candidates WHERE issue = ?", (issue,)
        ).fetchone()["count"]
        metrics = {
            "candidate_count": candidate_count,
            "generated": candidate is not None,
            "final_rank": candidate["final_rank"] if candidate else None,
            "hit_top10": bool(candidate and candidate["is_top10"]),
            "hit_top5": bool(candidate and candidate["is_top5"]),
        }
        feature_scores = json.loads(candidate["feature_scores_json"]) if candidate else {}
        updates: list[dict[str, Any]] = []
        rules = connection.execute(
            "SELECT * FROM p5_rules ORDER BY rule_id"
        ).fetchall()
        successful = bool(candidate and candidate["final_rank"] <= 100)
        review_has_lock = candidate_count == 10_000
        active_remaining = sum(bool(row["active"]) for row in rules)
        for row in rules:
            if not row["active"]:
                updates.append(
                    {
                        "rule_id": row["rule_id"],
                        "evidence": "paused",
                        "observations": row["positive_count"] + row["negative_count"],
                        "weight": round(float(row["weight"]), 6),
                        "active": False,
                        "retuned": False,
                        "paused": False,
                    }
                )
                continue
            positive = (
                review_has_lock
                and successful
                and feature_scores.get(row["rule_id"], 0) >= 0.5
            )
            positive_count = row["positive_count"] + int(positive)
            negative_count = row["negative_count"] + int(review_has_lock and not positive)
            observations = positive_count + negative_count
            previous_weight = float(row["weight"])
            weight = previous_weight
            # Accumulate evidence immediately, but never retune from a single draw.
            if review_has_lock and observations >= RULE_WEIGHT_MIN_OBSERVATIONS:
                performance = positive_count / observations
                weight = min(0.45, max(0.05, weight + (performance - 0.5) * 0.01))
            should_pause = (
                review_has_lock
                and observations >= RULE_PAUSE_MIN_OBSERVATIONS
                and positive_count / observations < RULE_PAUSE_POSITIVE_RATE
                and active_remaining > 1
            )
            active = not should_pause
            if should_pause:
                active_remaining -= 1
            connection.execute(
                """
                UPDATE p5_rules SET weight = ?, positive_count = ?, negative_count = ?,
                    active = ?, updated_at = ? WHERE rule_id = ?
                """,
                (
                    weight,
                    positive_count,
                    negative_count,
                    int(active),
                    created_at,
                    row["rule_id"],
                ),
            )
            updates.append(
                {
                    "rule_id": row["rule_id"],
                    "evidence": (
                        "not_applicable"
                        if not review_has_lock
                        else "positive" if positive else "negative"
                    ),
                    "observations": observations,
                    "weight": round(weight, 6),
                    "active": active,
                    "retuned": weight != previous_weight,
                    "paused": should_pause,
                }
            )
        connection.execute(
            """
            INSERT INTO p5_reviews(issue, official_result, metrics_json, rule_updates_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                issue,
                result,
                json.dumps(metrics, sort_keys=True),
                json.dumps(updates, sort_keys=True),
                created_at,
            ),
        )
        self._audit(
            connection,
            "review.completed",
            issue,
            {"official_result": result, "metrics": metrics, "rule_updates": updates},
            created_at,
        )
        return {
            "issue": issue,
            "official_result": result,
            "metrics": metrics,
            "rule_updates": updates,
            "reused": False,
        }

    def _generate_candidates(
        self, connection: sqlite3.Connection, issue: str, created_at: str
    ) -> list[tuple[Any, ...]]:
        rule_rows = connection.execute(
            "SELECT rule_id, weight, active FROM p5_rules"
        ).fetchall()
        if {row["rule_id"] for row in rule_rows} != {item[0] for item in RULES}:
            raise RuntimeError("P5 scoring rules are incomplete")
        rules = {
            row["rule_id"]: float(row["weight"])
            for row in rule_rows
            if row["active"]
        }
        if not rules:
            raise RuntimeError("P5 scoring requires at least one active rule")
        seed = f"{issue}|{MODEL_VERSION}"
        selected = sorted(
            range(100_000),
            key=lambda value: hashlib.sha256(
                f"{seed}|candidate|{value:05d}".encode()
            ).digest(),
        )[:10_000]
        scored: list[dict[str, Any]] = []
        total_weight = sum(rules.values())
        for generated_order, value in enumerate(selected, start=1):
            number = f"{value:05d}"
            digits = [int(digit) for digit in number]
            counts = {digit: digits.count(digit) for digit in set(digits)}
            features = {
                "digit_balance": max(0.0, 1 - abs(sum(digits) - 22.5) / 22.5),
                "digit_diversity": len(set(digits)) / 5,
                "adjacency_control": 1 - sum(
                    left == right for left, right in zip(digits, digits[1:])
                )
                / 4,
                "odd_even_balance": 1
                - abs(sum(digit % 2 for digit in digits) - 2.5) / 2.5,
                "deterministic_signal": int.from_bytes(
                    hashlib.sha256(f"{seed}|signal|{number}".encode()).digest()[:8],
                    "big",
                )
                / ((1 << 64) - 1),
            }
            filters: list[str] = []
            if len(set(digits)) <= 2:
                filters.append("low_digit_diversity")
            if max(counts.values()) >= 3:
                filters.append("triple_repeat")
            if digits == sorted(digits) or digits == sorted(digits, reverse=True):
                filters.append("monotonic_pattern")
            raw_score = sum(features[key] * weight for key, weight in rules.items()) / total_weight
            adjusted_score = max(0.0, raw_score - 0.075 * len(filters))
            scored.append(
                {
                    "number": number,
                    "generated_order": generated_order,
                    "raw_score": raw_score,
                    "adjusted_score": adjusted_score,
                    "feature_scores": features,
                    "filters_triggered": filters,
                }
            )
        preliminary = sorted(
            scored, key=lambda item: (-item["adjusted_score"], item["number"])
        )
        diverse_top: list[dict[str, Any]] = []
        remaining = preliminary.copy()
        while remaining and len(diverse_top) < 10:
            index = next(
                (
                    position
                    for position, candidate in enumerate(remaining[:1000])
                    if all(
                        sum(a != b for a, b in zip(candidate["number"], prior["number"])) >= 2
                        for prior in diverse_top
                    )
                ),
                0,
            )
            diverse_top.append(remaining.pop(index))
        final = diverse_top + remaining
        rows: list[tuple[Any, ...]] = []
        for final_rank, candidate in enumerate(final, start=1):
            survived = final_rank <= 100
            if survived:
                elimination_reason = None
            elif candidate["filters_triggered"]:
                elimination_reason = "filtered:" + ",".join(candidate["filters_triggered"])
            else:
                elimination_reason = "outside_final_100"
            rows.append(
                (
                    issue,
                    candidate["number"],
                    candidate["generated_order"],
                    round(candidate["raw_score"], 10),
                    round(candidate["adjusted_score"], 10),
                    json.dumps(candidate["feature_scores"], sort_keys=True),
                    json.dumps(candidate["filters_triggered"], sort_keys=True),
                    elimination_reason,
                    int(survived),
                    final_rank,
                    int(final_rank <= 10),
                    int(final_rank <= 5),
                    MODEL_VERSION,
                    created_at,
                )
            )
        return rows

    def home(self) -> dict[str, Any]:
        with self.connect() as connection:
            latest = connection.execute(
                """
                SELECT *, (SELECT COUNT(*) FROM p5_candidates c WHERE c.issue = i.issue)
                    AS candidate_count
                FROM p5_issues i ORDER BY COALESCE(locked_at, updated_at) DESC LIMIT 1
                """
            ).fetchone()
            top = []
            if latest is not None:
                top = connection.execute(
                    """
                    SELECT number, final_rank, adjusted_score, is_top10, is_top5
                    FROM p5_candidates WHERE issue = ? AND final_rank <= 10 ORDER BY final_rank
                    """,
                    (latest["issue"],),
                ).fetchall()
            review_count = connection.execute(
                "SELECT COUNT(*) AS count FROM p5_reviews"
            ).fetchone()["count"]
        return {
            "project": "p5",
            "schedule": "Asia/Shanghai 22:22, wait and retry until official result is confirmed",
            "execution_path": "gpt/chatgpt",
            "codex_invoked": False,
            "paper_only": True,
            **_research_boundary(),
            "latest_issue": _row_dict(latest) if latest else None,
            "top10": [_row_dict(row) for row in top],
            "review_count": review_count,
        }

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        limit = min(200, max(1, limit))
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT i.*,
                    (SELECT COUNT(*) FROM p5_candidates c WHERE c.issue = i.issue) AS candidate_count,
                    r.metrics_json, r.rule_updates_json, r.created_at AS reviewed_at
                FROM p5_issues i LEFT JOIN p5_reviews r ON r.issue = i.issue
                ORDER BY i.issue DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_row_dict(row) for row in rows]

    def research_boundary(self) -> dict[str, Any]:
        return _research_boundary()

    def candidate(
        self, issue: str, number: str | None = None, limit: int = 100
    ) -> dict[str, Any]:
        issue = _validate_issue(issue)
        limit = min(500, max(1, limit))
        with self.connect() as connection:
            if number is not None:
                number = _validate_number(number)
                row = connection.execute(
                    "SELECT * FROM p5_candidates WHERE issue = ? AND number = ?",
                    (issue, number),
                ).fetchone()
                return {
                    "issue": issue,
                    "number": number,
                    "generated": row is not None,
                    "candidate": _row_dict(row) if row else None,
                    **_research_boundary(),
                }
            rows = connection.execute(
                """
                SELECT * FROM p5_candidates WHERE issue = ?
                ORDER BY final_rank LIMIT ?
                """,
                (issue, limit),
            ).fetchall()
            count = connection.execute(
                "SELECT COUNT(*) AS count FROM p5_candidates WHERE issue = ?", (issue,)
            ).fetchone()["count"]
        return {
            "issue": issue,
            "candidate_count": count,
            "items": [_row_dict(row) for row in rows],
            **_research_boundary(),
        }

    def audit(self, limit: int = 100) -> dict[str, Any]:
        limit = min(500, max(1, limit))
        with self.connect() as connection:
            rules = connection.execute(
                "SELECT * FROM p5_rules ORDER BY rule_id"
            ).fetchall()
            events = connection.execute(
                "SELECT * FROM p5_audit ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return {
            "model_version": MODEL_VERSION,
            "workflow_version": WORKFLOW_VERSION,
            "execution_path": "gpt/chatgpt",
            "codex_invoked": False,
            "paper_only": True,
            **_research_boundary(),
            "rules": [_row_dict(row) for row in rules],
            "events": [_row_dict(row) for row in events],
        }


class P5Project:
    metadata = ProjectMetadata(
        id="p5",
        name="P5 / 排列5",
        description="Isolated daily 10xthink research workflow with complete candidate auditability.",
        icon="digits",
    )

    def __init__(self, storage_path: Path | None = None) -> None:
        self._storage_path = storage_path or Path("data/projects/p5/p5.db")
        self._store: P5Store | None = None

    @property
    def store(self) -> P5Store:
        if self._store is None:
            self._store = P5Store(self._storage_path)
        return self._store

    def context(self) -> dict[str, Any]:
        return {
            "scope": "p5-plugin-only",
            "game": "排列5",
            "workflow": WORKFLOW_VERSION,
            "daily_order": [
                "confirm previous official result after 22:22 Asia/Shanghai",
                "review the settled issue",
                "update cumulative rule evidence",
                "persist exactly 10000 next-issue candidates",
                "run 10xthink scoring, filtering, and dehomogenization",
                "record diagnostic Top10 then Top5 prefixes",
                "append an audit record",
            ],
            "execution_path": "gpt/chatgpt",
            "forbidden_execution_path": "codex",
            "paper_only": True,
            **_research_boundary(),
            "isolation": "No P3 access and no P5 fields in core Chat, Memory, or Repository schemas.",
        }

    def tools(self) -> set[str]:
        return {
            "p5.status",
            "p5.history",
            "p5.candidate.lookup",
            "p5.daily.run",
            "p5.audit",
        }

    def views(self) -> list[ProjectView]:
        return [
            ProjectView(id="home", label="P5 Home", route="/projects/p5"),
            ProjectView(id="history", label="History", route="/projects/p5/history"),
            ProjectView(
                id="candidates", label="Candidate Explorer", route="/projects/p5/candidates"
            ),
            ProjectView(id="audit", label="Model Audit", route="/projects/p5/audit"),
        ]

    def artifact_kinds(self) -> set[str]:
        return {"p5-candidate-lock", "p5-review", "p5-model-audit"}

    def permissions(self) -> dict[str, list[str]]:
        return {
            "tools": sorted(self.tools()),
            "files": ["data/projects/p5/**"],
            "providers": ["openai"],
            "denied_projects": ["p3"],
            "denied_providers": ["codex"],
        }
