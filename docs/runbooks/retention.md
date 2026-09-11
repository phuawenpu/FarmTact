# Anonymous tenant retention

FarmTact anonymous sessions authenticate for 24 hours. Expiry prevents later use of the session cookie, but it does not itself delete the tenant's durable rows. `scripts/prune_expired_tenants.py` is the explicit operator maintenance command for removing old inactive anonymous tenants.

The command is a dry run unless `--apply` is present. It is not imported by the application, is not scheduled by the worker, and exposes no HTTP endpoint. Retention must be invoked deliberately by an operator. Like every existing `Store` construction, CLI startup registers the application metadata and may create missing tables through additive `metadata.create_all`; dry-run mode performs no tenant-row deletion but should still target the intended database.

## Safety policy

- Retention must be at least seven days; the default is 30 days.
- Each invocation inspects at most 100 tenants by default and never more than 500.
- The cutoff is exclusive: a tenant must have `created_at` earlier than `as_of - retained_days`.
- A tenant is retained if any planning mission, scenario, conversation request, or Council Research calculation is queued or running. Planning status `CREATED` is treated as queued.
- Apply mode locks candidate tenant rows, repeats the active-job checks inside one write transaction, deletes tenant-owned children in foreign-key dependency order, and deletes the tenant row last.
- The deletion inventory is derived from all registered SQLAlchemy tables. A newly registered table with `tenant_id` is included automatically. A newly registered shared table causes retention to fail until its policy is reviewed.
- Shared inference budgets, abuse-rate counters, security settings, and edition-control reservation/release records are explicitly protected.
- Invalid or timezone-naive tenant creation timestamps are skipped.

The command does not erase provider-wide budgets or security controls. It does not perform secure backup destruction, external log deletion, or data-subject identity verification; those require separate operator policies.

## Preview

Set `FARMTACT_DATABASE_URL` through the normal secret/configuration mechanism. Do not put a credential-bearing URL in shell history.

```bash
.venv/bin/python scripts/prune_expired_tenants.py \
  --retained-days 30 \
  --limit 100
```

The JSON result identifies eligible tenant IDs, active tenants that were skipped, invalid timestamps, the registered/protected table inventory, and row counts that would be removed. `mode` must be `dry_run`, `deleted_rows` must be empty, and `automatic_schedule` must be false.

Review the dry-run output and confirm that the configured database and cutoff are the intended maintenance target before applying it.

## Apply the reviewed batch

Use exactly the reviewed retention period and bound:

```bash
.venv/bin/python scripts/prune_expired_tenants.py \
  --retained-days 30 \
  --limit 100 \
  --apply
```

Apply mode returns `mode=apply`, the eligible and skipped tenant sets, expected row counts, and committed deletion counts. The entire bounded batch is one transaction. A database error rolls it back.

Repeat the dry run after an applied batch. Because candidate selection is bounded and ordered oldest first, multiple reviewed invocations may be required. Do not add this command to the hourly application worker or a deployment startup hook.

## Verification and recovery

The focused test uses a fresh in-memory SQLite database and proves:

- dry-run leaves every row unchanged;
- an old inactive tenant is removed from all current tenant-owned tables;
- shared security and inference-budget records remain;
- recent tenants and old tenants with active jobs in each supported queue remain;
- the tenant bound limits one invocation;
- retention-period and tenant-count bounds reject invalid inputs.

The command has no undo function. Recovery of an incorrectly selected production tenant requires the normal authorized database backup and restore procedure. Preserve the dry-run and apply JSON outputs in the operator's maintenance record without adding session cookies, database URLs, or raw tenant payloads.

## Remaining policy gap

This command supplies a bounded deletion mechanism, but FarmTact still needs an approved retention schedule, named operator responsibility, backup-retention alignment, audit-log handling, and a data-subject deletion process before anonymous-state lifecycle can be called operationally complete. No automatic production deletion is enabled.
