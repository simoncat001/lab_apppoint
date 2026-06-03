import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

async def fix_project():
    async with AsyncSessionLocal() as session:
        print("Creating default Project...")
        # Check if project exists (double check)
        res = await session.execute(text("SELECT id FROM project WHERE id = 1"))
        if res.fetchone():
            print("Project 1 already exists via double check.")
        else:
            # We strictly need id=1 because reservation links to it
            await session.execute(
                text("INSERT INTO project (id, name, account_id, active) VALUES (:id, :name, :account_id, :active)"),
                {"id": 1, "name": "Default Project", "account_id": 1, "active": 1}
            )
            await session.commit()
            print("Created Project 1 linked to Account 1.")

if __name__ == "__main__":
    asyncio.run(fix_project())
