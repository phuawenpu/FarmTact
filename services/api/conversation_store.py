"""Tenant-scoped persistence for advisor conversations.

The tables register on the application's existing SQLAlchemy metadata.  The
adapter deliberately uses :class:`services.api.store.Store` transactions and
connections so a conversation cannot acquire a second database or transaction
policy by accident.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Table,
    UniqueConstraint,
    func,
    select,
    update,
)

from services.api.store import metadata, now, tenants

MAX_CONVERSATIONS_PER_TENANT = 30
MAX_MESSAGES_PER_CONVERSATION = 120
CONVERSATION_LIST_LIMIT = 30

conversations = Table(
    "conversations",
    metadata,
    Column("id", String, primary_key=True),
    Column("tenant_id", String, ForeignKey(tenants.c.id), nullable=False),
    Column("idempotency_key", String, nullable=False),
    Column("request_hash", String, nullable=False),
    Column("status", String, nullable=False),
    Column("payload", JSON, nullable=False),
    UniqueConstraint("tenant_id", "idempotency_key", name="conversation_idempotency"),
    UniqueConstraint("id", "tenant_id", name="conversation_tenant_identity"),
)

conversation_messages = Table(
    "conversation_messages",
    metadata,
    Column("id", String, primary_key=True),
    Column("conversation_id", String, nullable=False),
    Column("tenant_id", String, ForeignKey(tenants.c.id), nullable=False),
    Column("sequence", Integer, nullable=False),
    Column("payload", JSON, nullable=False),
    UniqueConstraint("conversation_id", "sequence", name="conversation_message_sequence"),
    UniqueConstraint(
        "id", "conversation_id", "tenant_id", name="conversation_message_identity"
    ),
    ForeignKeyConstraint(
        ["conversation_id", "tenant_id"],
        ["conversations.id", "conversations.tenant_id"],
        name="conversation_message_tenant_fk",
    ),
)

conversation_requests = Table(
    "conversation_requests",
    metadata,
    Column("id", String, primary_key=True),
    Column("conversation_id", String, nullable=False),
    Column("tenant_id", String, ForeignKey(tenants.c.id), nullable=False),
    Column("idempotency_key", String, nullable=False),
    Column("request_hash", String, nullable=False),
    Column("status", String, nullable=False),
    Column("payload", JSON, nullable=False),
    UniqueConstraint(
        "conversation_id",
        "tenant_id",
        "idempotency_key",
        name="conversation_request_idempotency",
    ),
    UniqueConstraint(
        "id", "conversation_id", "tenant_id", name="conversation_request_identity"
    ),
    ForeignKeyConstraint(
        ["conversation_id", "tenant_id"],
        ["conversations.id", "conversations.tenant_id"],
        name="conversation_request_tenant_fk",
    ),
)

conversation_events = Table(
    "conversation_events",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("conversation_id", String, nullable=False),
    Column("tenant_id", String, ForeignKey(tenants.c.id), nullable=False),
    Column("request_id", String, nullable=True),
    Column("sequence", Integer, nullable=False),
    Column("payload", JSON, nullable=False),
    UniqueConstraint("conversation_id", "sequence", name="conversation_event_sequence"),
    ForeignKeyConstraint(
        ["conversation_id", "tenant_id"],
        ["conversations.id", "conversations.tenant_id"],
        name="conversation_event_tenant_fk",
    ),
    ForeignKeyConstraint(
        ["request_id", "conversation_id", "tenant_id"],
        [
            "conversation_requests.id",
            "conversation_requests.conversation_id",
            "conversation_requests.tenant_id",
        ],
        name="conversation_event_request_fk",
    ),
)


class ConversationStore:
    """Persistence adapter over the application's existing ``Store``."""

    def __init__(self, store: Any) -> None:
        self.store = store

    def create_conversation(
        self,
        tenant: str,
        key: str,
        request_hash: str,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], bool]:
        from services.api.provenance import runtime_provenance
        payload.setdefault('runtime_provenance',runtime_provenance())
        with self.store.connection(write=True) as connection:
            connection.execute(
                select(tenants.c.id).where(tenants.c.id == tenant).with_for_update()
            )
            existing = connection.execute(
                select(conversations).where(
                    conversations.c.tenant_id == tenant,
                    conversations.c.idempotency_key == key,
                )
            ).mappings().first()
            if existing:
                if existing["request_hash"] != request_hash:
                    raise ValueError("Idempotency key reused with changed conversation inputs")
                return existing["payload"], False
            count = connection.execute(
                select(func.count()).select_from(conversations).where(
                    conversations.c.tenant_id == tenant
                )
            ).scalar_one()
            if count >= MAX_CONVERSATIONS_PER_TENANT:
                raise ValueError("Thirty conversations per session maximum")
            connection.execute(
                conversations.insert().values(
                    id=payload["id"],
                    tenant_id=tenant,
                    idempotency_key=key,
                    request_hash=request_hash,
                    status=payload["status"],
                    payload=payload,
                )
            )
        return payload, True

    def list_conversations(
        self, tenant: str, *, limit: int = CONVERSATION_LIST_LIMIT, before: str | None = None
    ) -> list[dict[str, Any]]:
        if not 1 <= limit <= CONVERSATION_LIST_LIMIT:
            raise ValueError("Conversation list limit must be from 1 to 30")
        with self.store.connection() as connection:
            updated = conversations.c.payload["updated_at"].as_string()
            query = select(conversations.c.payload).where(conversations.c.tenant_id == tenant)
            if before is not None:
                query = query.where(updated < before)
            rows = connection.execute(
                query.order_by(updated.desc(), conversations.c.id.desc()).limit(limit)
            ).scalars().all()
        return list(rows)

    def get_conversation_by_key(
        self, tenant: str, key: str
    ) -> tuple[dict[str, Any], str] | None:
        with self.store.connection() as connection:
            row = connection.execute(
                select(conversations.c.payload, conversations.c.request_hash).where(
                    conversations.c.tenant_id == tenant,
                    conversations.c.idempotency_key == key,
                )
            ).first()
        return (row[0], row[1]) if row else None

    def get_conversation(self, tenant: str, conversation_id: str) -> dict[str, Any] | None:
        with self.store.connection() as connection:
            return connection.execute(
                select(conversations.c.payload).where(
                    conversations.c.id == conversation_id,
                    conversations.c.tenant_id == tenant,
                )
            ).scalar_one_or_none()

    def save_conversation(self, tenant: str, payload: dict[str, Any]) -> None:
        with self.store.connection(write=True) as connection:
            changed = connection.execute(
                update(conversations)
                .where(
                    conversations.c.id == payload["id"],
                    conversations.c.tenant_id == tenant,
                )
                .values(status=payload["status"], payload=payload)
            )
            if changed.rowcount != 1:
                raise ValueError("Conversation not owned by tenant")

    def list_messages(self, tenant: str, conversation_id: str) -> list[dict[str, Any]]:
        with self.store.connection() as connection:
            return list(
                connection.execute(
                    select(conversation_messages.c.payload)
                    .where(
                        conversation_messages.c.tenant_id == tenant,
                        conversation_messages.c.conversation_id == conversation_id,
                    )
                    .order_by(conversation_messages.c.sequence)
                ).scalars()
            )

    def get_message(
        self, tenant: str, conversation_id: str, message_id: str
    ) -> dict[str, Any] | None:
        with self.store.connection() as connection:
            return connection.execute(
                select(conversation_messages.c.payload).where(
                    conversation_messages.c.id == message_id,
                    conversation_messages.c.conversation_id == conversation_id,
                    conversation_messages.c.tenant_id == tenant,
                )
            ).scalar_one_or_none()

    def _append_message_locked(
        self,
        connection: Any,
        tenant: str,
        conversation_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        owner = connection.execute(
            select(conversations.c.id)
            .where(
                conversations.c.id == conversation_id,
                conversations.c.tenant_id == tenant,
            )
            .with_for_update()
        ).scalar_one_or_none()
        if owner is None:
            raise ValueError("Conversation not owned by tenant")
        sequence = (
            connection.execute(
                select(conversation_messages.c.sequence)
                .where(
                    conversation_messages.c.conversation_id == conversation_id,
                    conversation_messages.c.tenant_id == tenant,
                )
                .order_by(conversation_messages.c.sequence.desc())
                .limit(1)
            ).scalar_one_or_none()
            or 0
        ) + 1
        saved = dict(payload, conversation_id=conversation_id, sequence=sequence)
        connection.execute(
            conversation_messages.insert().values(
                id=saved["id"],
                conversation_id=conversation_id,
                tenant_id=tenant,
                sequence=sequence,
                payload=saved,
            )
        )
        return saved

    def append_message(
        self, tenant: str, conversation_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        with self.store.connection(write=True) as connection:
            return self._append_message_locked(
                connection, tenant, conversation_id, payload
            )

    def create_request(
        self,
        tenant: str,
        conversation_id: str,
        key: str,
        request_hash: str,
        payload: dict[str, Any],
        user_message: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], bool]:
        """Atomically append one user turn and enqueue its inference request."""

        with self.store.connection(write=True) as connection:
            connection.execute(
                select(conversations.c.id)
                .where(
                    conversations.c.id == conversation_id,
                    conversations.c.tenant_id == tenant,
                )
                .with_for_update()
            )
            existing = connection.execute(
                select(conversation_requests).where(
                    conversation_requests.c.conversation_id == conversation_id,
                    conversation_requests.c.tenant_id == tenant,
                    conversation_requests.c.idempotency_key == key,
                )
            ).mappings().first()
            if existing:
                if existing["request_hash"] != request_hash:
                    raise ValueError("Idempotency key reused with changed conversation inputs")
                existing_message = connection.execute(
                    select(conversation_messages.c.payload).where(
                        conversation_messages.c.id == existing["payload"]["user_message_id"],
                        conversation_messages.c.conversation_id == conversation_id,
                        conversation_messages.c.tenant_id == tenant,
                    )
                ).scalar_one()
                return existing["payload"], existing_message, False
            active = connection.execute(
                select(conversation_requests.c.id).where(
                    conversation_requests.c.conversation_id == conversation_id,
                    conversation_requests.c.tenant_id == tenant,
                    conversation_requests.c.status.in_(["QUEUED", "RUNNING"]),
                )
            ).first()
            if active:
                raise ValueError("A conversation response is already running")
            existing_messages = connection.execute(
                select(func.count()).select_from(conversation_messages).where(
                    conversation_messages.c.conversation_id == conversation_id,
                    conversation_messages.c.tenant_id == tenant,
                )
            ).scalar_one()
            required = 1 + len(payload.get("roles", []))
            if existing_messages + required > MAX_MESSAGES_PER_CONVERSATION:
                raise ValueError("Conversation message limit reached")
            saved_message = self._append_message_locked(
                connection, tenant, conversation_id, user_message
            )
            request_payload = dict(payload, user_message_id=saved_message["id"])
            connection.execute(
                conversation_requests.insert().values(
                    id=request_payload["id"],
                    conversation_id=conversation_id,
                    tenant_id=tenant,
                    idempotency_key=key,
                    request_hash=request_hash,
                    status=request_payload["status"],
                    payload=request_payload,
                )
            )
            conversation = connection.execute(
                select(conversations.c.payload).where(
                    conversations.c.id == conversation_id,
                    conversations.c.tenant_id == tenant,
                )
            ).scalar_one()
            updated_conversation = dict(
                conversation,
                status="QUEUED",
                updated_at=now(),
                last_request_id=request_payload["id"],
                last_request_status="QUEUED",
            )
            connection.execute(
                update(conversations)
                .where(
                    conversations.c.id == conversation_id,
                    conversations.c.tenant_id == tenant,
                )
                .values(status="QUEUED", payload=updated_conversation)
            )
        return request_payload, saved_message, True

    def get_request(self, tenant: str, request_id: str) -> dict[str, Any] | None:
        with self.store.connection() as connection:
            return connection.execute(
                select(conversation_requests.c.payload).where(
                    conversation_requests.c.id == request_id,
                    conversation_requests.c.tenant_id == tenant,
                )
            ).scalar_one_or_none()

    def get_request_by_key(
        self, tenant: str, conversation_id: str, key: str
    ) -> tuple[dict[str, Any], str, dict[str, Any]] | None:
        with self.store.connection() as connection:
            row = connection.execute(
                select(conversation_requests).where(
                    conversation_requests.c.tenant_id == tenant,
                    conversation_requests.c.conversation_id == conversation_id,
                    conversation_requests.c.idempotency_key == key,
                )
            ).mappings().first()
            if not row:
                return None
            message = connection.execute(
                select(conversation_messages.c.payload).where(
                    conversation_messages.c.id == row["payload"]["user_message_id"],
                    conversation_messages.c.conversation_id == conversation_id,
                    conversation_messages.c.tenant_id == tenant,
                )
            ).scalar_one()
        return row["payload"], row["request_hash"], message

    def save_request(self, tenant: str, payload: dict[str, Any]) -> None:
        with self.store.connection(write=True) as connection:
            changed = connection.execute(
                update(conversation_requests)
                .where(
                    conversation_requests.c.id == payload["id"],
                    conversation_requests.c.tenant_id == tenant,
                )
                .values(status=payload["status"], payload=payload)
            )
            if changed.rowcount != 1:
                raise ValueError("Conversation request not owned by tenant")

    def pending(self) -> list[tuple[str, str]]:
        with self.store.connection() as connection:
            return list(
                connection.execute(
                    select(
                        conversation_requests.c.tenant_id,
                        conversation_requests.c.id,
                    ).where(conversation_requests.c.status == "QUEUED")
                ).all()
            )

    def claim(self, tenant: str, request_id: str) -> bool:
        with self.store.connection(write=True) as connection:
            row = connection.execute(
                select(conversation_requests)
                .where(
                    conversation_requests.c.id == request_id,
                    conversation_requests.c.tenant_id == tenant,
                )
                .with_for_update()
            ).mappings().first()
            if not row or row["status"] != "QUEUED":
                return False
            payload = dict(row["payload"], status="RUNNING", started_at=now())
            connection.execute(
                update(conversation_requests)
                .where(
                    conversation_requests.c.id == request_id,
                    conversation_requests.c.tenant_id == tenant,
                    conversation_requests.c.status == "QUEUED",
                )
                .values(status="RUNNING", payload=payload)
            )
            return True

    def cancel_request(
        self, tenant: str, conversation_id: str, request_id: str
    ) -> tuple[dict[str, Any] | None, bool]:
        """Atomically mark queued/running work cancelled; terminal calls are idempotent."""

        with self.store.connection(write=True) as connection:
            row = connection.execute(
                select(conversation_requests)
                .where(
                    conversation_requests.c.id == request_id,
                    conversation_requests.c.conversation_id == conversation_id,
                    conversation_requests.c.tenant_id == tenant,
                )
                .with_for_update()
            ).mappings().first()
            if not row:
                return None, False
            payload = row["payload"]
            if row["status"] not in ("QUEUED", "RUNNING"):
                return payload, False
            cancelled_at = now()
            payload = dict(
                payload,
                status="CANCELLED",
                execution_status="cancelled",
                cancelled_at=cancelled_at,
                completed_at=cancelled_at,
                error="Cancellation recorded before another advisor turn; completed messages were preserved.",
            )
            changed = connection.execute(
                update(conversation_requests)
                .where(
                    conversation_requests.c.id == request_id,
                    conversation_requests.c.conversation_id == conversation_id,
                    conversation_requests.c.tenant_id == tenant,
                    conversation_requests.c.status.in_(["QUEUED", "RUNNING"]),
                )
                .values(status="CANCELLED", payload=payload)
            )
            if changed.rowcount != 1:
                current = connection.execute(
                    select(conversation_requests.c.payload).where(
                        conversation_requests.c.id == request_id,
                        conversation_requests.c.conversation_id == conversation_id,
                        conversation_requests.c.tenant_id == tenant,
                    )
                ).scalar_one_or_none()
                return current, False
            conversation = connection.execute(
                select(conversations.c.payload).where(
                    conversations.c.id == conversation_id,
                    conversations.c.tenant_id == tenant,
                )
            ).scalar_one()
            updated_conversation = dict(
                conversation,
                status="OPEN",
                updated_at=cancelled_at,
                last_request_id=request_id,
                last_request_status="CANCELLED",
                last_execution_status="cancelled",
                last_evidence_status=payload.get("evidence_status", "not_evaluated"),
                last_decision_influence="none_cancelled",
            )
            connection.execute(
                update(conversations)
                .where(
                    conversations.c.id == conversation_id,
                    conversations.c.tenant_id == tenant,
                )
                .values(status="OPEN", payload=updated_conversation)
            )
            return payload, True

    def is_cancelled(self, tenant: str, request_id: str) -> bool:
        with self.store.connection() as connection:
            return connection.execute(
                select(conversation_requests.c.status).where(
                    conversation_requests.c.id == request_id,
                    conversation_requests.c.tenant_id == tenant,
                )
            ).scalar_one_or_none() == "CANCELLED"

    def append_event(
        self,
        tenant: str,
        conversation_id: str,
        request_id: str | None,
        event_type: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        with self.store.connection(write=True) as connection:
            owner = connection.execute(
                select(conversations.c.id)
                .where(
                    conversations.c.id == conversation_id,
                    conversations.c.tenant_id == tenant,
                )
                .with_for_update()
            ).scalar_one_or_none()
            if owner is None:
                raise ValueError("Conversation not owned by tenant")
            if request_id is not None:
                request_owner = connection.execute(
                    select(conversation_requests.c.id).where(
                        conversation_requests.c.id == request_id,
                        conversation_requests.c.conversation_id == conversation_id,
                        conversation_requests.c.tenant_id == tenant,
                    )
                ).scalar_one_or_none()
                if request_owner is None:
                    raise ValueError("Conversation request not owned by tenant")
            sequence = (
                connection.execute(
                    select(conversation_events.c.sequence)
                    .where(
                        conversation_events.c.conversation_id == conversation_id,
                        conversation_events.c.tenant_id == tenant,
                    )
                    .order_by(conversation_events.c.sequence.desc())
                    .limit(1)
                ).scalar_one_or_none()
                or 0
            ) + 1
            event = {
                "conversation_id": conversation_id,
                "request_id": request_id,
                "sequence": sequence,
                "occurred_at": now(),
                "event_type": event_type,
                "schema_version": "1.0",
                "body": body,
            }
            connection.execute(
                conversation_events.insert().values(
                    conversation_id=conversation_id,
                    tenant_id=tenant,
                    request_id=request_id,
                    sequence=sequence,
                    payload=event,
                )
            )
        return event

    def get_events(
        self, tenant: str, conversation_id: str, after: int = 0
    ) -> list[dict[str, Any]]:
        with self.store.connection() as connection:
            return list(
                connection.execute(
                    select(conversation_events.c.payload)
                    .where(
                        conversation_events.c.conversation_id == conversation_id,
                        conversation_events.c.tenant_id == tenant,
                        conversation_events.c.sequence > after,
                    )
                    .order_by(conversation_events.c.sequence)
                ).scalars()
            )

    def interrupt_abandoned(self) -> int:
        """Persist partial state without re-queueing possibly paid work."""

        interrupted = 0
        with self.store.connection(write=True) as connection:
            rows = connection.execute(
                select(conversation_requests).where(
                    conversation_requests.c.status == "RUNNING"
                )
            ).mappings().all()
            for row in rows:
                request_payload = dict(
                    row["payload"],
                    status="INTERRUPTED",
                    completed_at=now(),
                    error="Worker restarted during advisor response; completed messages were preserved and inference was not repeated.",
                )
                connection.execute(
                    update(conversation_requests)
                    .where(conversation_requests.c.id == row["id"])
                    .values(status="INTERRUPTED", payload=request_payload)
                )
                conversation = connection.execute(
                    select(conversations.c.payload).where(
                        conversations.c.id == row["conversation_id"],
                        conversations.c.tenant_id == row["tenant_id"],
                    )
                ).scalar_one()
                updated_conversation = dict(
                    conversation,
                    status="PARTIAL",
                    updated_at=now(),
                    last_request_id=row["id"],
                    last_request_status="INTERRUPTED",
                )
                connection.execute(
                    update(conversations)
                    .where(conversations.c.id == row["conversation_id"])
                    .values(status="PARTIAL", payload=updated_conversation)
                )
                interrupted += 1
        return interrupted
