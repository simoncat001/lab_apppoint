import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal


async def main(bill_id: int):
    async with AsyncSessionLocal() as session:
        bill = await session.execute(
            text("SELECT id, account_id, status FROM bill WHERE id = :id"),
            {"id": bill_id},
        )
        bill_row = bill.fetchone()
        if not bill_row:
            print(f"Bill {bill_id} not found")
            return

        account_id = int(bill_row[1])
        status = bill_row[2]
        print(f"Bill: id={bill_id} account_id={account_id} status={status}")

        print("\nProjects under this account:")
        projects = await session.execute(
            text("SELECT id, name, account_id FROM project WHERE account_id = :aid"),
            {"aid": account_id},
        )
        project_rows = projects.fetchall()
        for r in project_rows:
            print(f"  Project: {r}")
        project_ids = [int(r[0]) for r in project_rows]
        if not project_ids:
            print("  (none)")

        print("\nUsage events already attached to this bill:")
        res = await session.execute(
            text(
                """
                SELECT id, project_id, user_id, operator_id, validated, waived, bill_id, start, end, amount
                FROM usage_event
                WHERE bill_id = :bid
                ORDER BY start ASC
                """
            ),
            {"bid": bill_id},
        )
        rows = res.fetchall()
        print(f"  count={len(rows)}")
        for row in rows:
            print(f"  UsageEvent: {row}")

        print("\nUsage events billable to this account by project.account_id (all statuses):")
        res = await session.execute(
            text(
                """
                SELECT ue.id, ue.project_id, p.account_id, ue.user_id, ue.operator_id,
                       ue.validated, ue.waived, ue.bill_id, ue.start, ue.end, ue.amount
                FROM usage_event ue
                JOIN project p ON ue.project_id = p.id
                WHERE p.account_id = :aid
                ORDER BY ue.start ASC
                """
            ),
            {"aid": account_id},
        )
        all_rows = res.fetchall()
        print(f"  count={len(all_rows)}")
        for row in all_rows:
            print(f"  UsageEvent: {row}")

        print("\nUsage events that SHOULD be auto-attached by current rule (validated=1, waived=0, bill_id is null):")
        res = await session.execute(
            text(
                """
                SELECT ue.id, ue.project_id, ue.user_id, ue.operator_id, ue.validated, ue.waived, ue.bill_id, ue.amount
                FROM usage_event ue
                JOIN project p ON ue.project_id = p.id
                WHERE p.account_id = :aid
                  AND ue.validated = 1
                  AND ue.waived = 0
                  AND ue.bill_id IS NULL
                ORDER BY ue.start ASC
                """
            ),
            {"aid": account_id},
        )
        should = res.fetchall()
        print(f"  count={len(should)}")
        for row in should:
            print(f"  ToAttach: {row}")

        print("\nUsage events under this account but NOT eligible for auto-attach (why):")
        res = await session.execute(
            text(
                """
                SELECT ue.id,
                       ue.validated,
                       ue.waived,
                       ue.bill_id,
                       CASE
                           WHEN ue.validated = 0 THEN 'not_validated'
                           WHEN ue.waived = 1 THEN 'waived'
                           WHEN ue.bill_id IS NOT NULL THEN 'already_billed'
                           ELSE 'other'
                       END AS reason
                FROM usage_event ue
                JOIN project p ON ue.project_id = p.id
                WHERE p.account_id = :aid
                  AND NOT (ue.validated = 1 AND ue.waived = 0 AND ue.bill_id IS NULL)
                ORDER BY ue.start ASC
                """
            ),
            {"aid": account_id},
        )
        not_ok = res.fetchall()
        print(f"  count={len(not_ok)}")
        for row in not_ok:
            print(f"  NotEligible: {row}")


if __name__ == "__main__":
    import sys

    bill_id_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    asyncio.run(main(bill_id_arg))
