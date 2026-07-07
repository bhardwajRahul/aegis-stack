"""Import pipeline: batch bookkeeping + two-lane transaction dedup.

Shared by every importer (OFX/QFX, QIF, CSV). Each run creates a
``finance_import_batch`` — short-circuiting an identical re-upload by
``file_sha256`` — writes one ``finance_import_batch_row`` per record, and
inserts new transactions while counting duplicates. Writes but does not commit
(the caller owns the transaction boundary).

``finance_import_batch`` / ``_row`` carry a NOT-NULL ``owner_user_id``; in
standalone (no-auth) mode the owner is ``None``, so it's coerced to the ``0``
sentinel for those two tables (transactions stay nullable).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.services.finance.finance_service import FinanceService
from app.services.finance.importers.base import ImportResult, ParsedTransaction
from app.services.finance.models import (
    FinanceAccount,
    FinanceImportBatch,
    FinanceImportBatchRow,
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def _resolve_account_id(
    db: AsyncSession,
    *,
    owner_user_id: int | None,
    account_key: str | None,
    default_account_id: int | None,
) -> int | None:
    """Explicit account wins; else match the source account id; else None
    (never guess — an unresolved row is errored, not misfiled)."""
    if default_account_id is not None:
        return default_account_id
    if account_key:
        query = select(FinanceAccount.id).where(
            FinanceAccount.provider_account_id == account_key,
            FinanceAccount.deleted_at.is_(None),
        )
        if owner_user_id is not None:
            query = query.where(FinanceAccount.owner_user_id == owner_user_id)
        return (await db.exec(query)).first()
    return None


async def ingest_transactions(
    db: AsyncSession,
    *,
    owner_user_id: int | None,
    source_type: str,
    file_name: str | None,
    file_bytes: bytes,
    parsed: list[ParsedTransaction],
    default_account_id: int | None = None,
) -> ImportResult:
    """Ingest parsed transactions under a reversible, deduped import batch."""
    batch_owner = 0 if owner_user_id is None else owner_user_id
    file_sha256 = hashlib.sha256(file_bytes).hexdigest()

    # Identical re-upload short-circuit: return the prior batch, all-duplicate.
    prior = (
        await db.exec(
            select(FinanceImportBatch).where(
                FinanceImportBatch.owner_user_id == batch_owner,
                FinanceImportBatch.file_sha256 == file_sha256,
            )
        )
    ).first()
    if prior is not None:
        return ImportResult(
            batch_id=prior.id,
            rows_total=prior.rows_total,
            rows_duplicate=prior.rows_total,
        )

    batch = FinanceImportBatch(
        owner_user_id=batch_owner,
        source_type=source_type,
        file_name=file_name,
        file_sha256=file_sha256,
        status="processing",
        rows_total=len(parsed),
        started_at=_utcnow(),
    )
    db.add(batch)
    await db.flush()

    service = FinanceService(db)
    inserted = duplicate = error = 0
    for row_number, txn in enumerate(parsed, start=1):
        account_id = await _resolve_account_id(
            db,
            owner_user_id=owner_user_id,
            account_key=txn.account_key,
            default_account_id=default_account_id,
        )
        if account_id is None:
            error += 1
            db.add(
                FinanceImportBatchRow(
                    import_batch_id=batch.id,
                    owner_user_id=batch_owner,
                    row_number=row_number,
                    parsed_status="error",
                    reason="account not resolved",
                    content_hash=txn.import_hash,
                    fitid=txn.external_id,
                )
            )
            continue

        existing = await service.find_transaction(
            account_id=account_id,
            source=txn.source,
            external_id=txn.external_id,
            import_hash=txn.import_hash,
        )
        if existing is not None:
            duplicate += 1
            db.add(
                FinanceImportBatchRow(
                    import_batch_id=batch.id,
                    owner_user_id=batch_owner,
                    account_id=account_id,
                    row_number=row_number,
                    parsed_status="duplicate",
                    matched_transaction_id=existing.id,
                    content_hash=txn.import_hash,
                    fitid=txn.external_id,
                )
            )
            continue

        created = await service.create_transaction(
            owner_user_id=owner_user_id,
            account_id=account_id,
            amount=txn.amount,
            txn_date=txn.date,
            name=txn.name,
            source=txn.source,
            external_id=txn.external_id,
            external_id_source=txn.external_id_source,
            import_hash=txn.import_hash,
            import_batch_id=batch.id,
            raw_amount=txn.raw_amount,
            raw_sign_convention=txn.raw_sign_convention,
            original_description=txn.original_description,
            memo=txn.memo,
            check_number=txn.check_number,
        )
        inserted += 1
        db.add(
            FinanceImportBatchRow(
                import_batch_id=batch.id,
                owner_user_id=batch_owner,
                account_id=account_id,
                row_number=row_number,
                parsed_status="inserted",
                matched_transaction_id=created.id,
                content_hash=txn.import_hash,
                fitid=txn.external_id,
            )
        )

    batch.rows_inserted = inserted
    batch.rows_duplicate = duplicate
    batch.rows_error = error
    batch.status = "committed"
    batch.finished_at = _utcnow()
    db.add(batch)
    await db.flush()

    return ImportResult(
        batch_id=batch.id,
        rows_total=len(parsed),
        rows_inserted=inserted,
        rows_duplicate=duplicate,
        rows_error=error,
    )
