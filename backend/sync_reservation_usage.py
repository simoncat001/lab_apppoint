import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, and_, exists
from app.db.session import AsyncSessionLocal
from app.models.reservation import Reservation
from app.models.usage_event import UsageEvent
from app.models.bill import Bill
from app.models.tool import Tool
from app.services.usage_event_service import UsageEventService

async def sync_usage_from_reservations():
    async with AsyncSessionLocal() as session:
        print("Starting synchronization of reservations to usage events...")
        
        # 1. 查找所有已结束的、未取消的预约
        now = datetime.now(timezone.utc)
        query = select(Reservation).where(
            and_(
                Reservation.end < now,
                Reservation.cancelled == False
            )
        )
        
        result = await session.execute(query)
        reservations = result.scalars().all()
        
        count = 0
        
        for res in reservations:
            # 2. 检查是否有重叠的使用记录
            usage_query = select(UsageEvent).where(
                and_(
                    UsageEvent.tool_id == res.tool_id,
                    UsageEvent.user_id == res.user_id,
                    UsageEvent.start >= res.start - timedelta(minutes=5),
                    UsageEvent.start <= res.end
                )
            )
            usage_result = await session.execute(usage_query)
            existing_usage = usage_result.scalars().first()
            
            if existing_usage:
                print(f"Reservation {res.id} already has usage event {existing_usage.id}. Skipping.")
                continue
                
            print(f"Creating usage event for Reservation {res.id} (User: {res.user_id}, Tool: {res.tool_id})...")
            
            # Fetch Tool info
            tool_result = await session.execute(select(Tool).where(Tool.id == res.tool_id))
            tool = tool_result.scalars().first()
            if not tool:
                print(f"Tool {res.tool_id} not found. Skipping.")
                continue

            # 3. 创建使用记录
            usage_event = UsageEvent(
                user_id=res.user_id,
                operator_id=res.user_id,
                tool_id=res.tool_id,
                project_id=res.project_id,
                start=res.start,
                end=res.end,
                remote_work=False
            )
            session.add(usage_event)
            await session.flush()
            
            # 4. 计算费用
            amount = 0.0
            if tool.price_type == 1: # Hourly
                base_price = float(tool.price_per_hour) if tool.price_per_hour else 0.0
                amount = await UsageEventService._calculate_cost(session, tool.id, usage_event.start, usage_event.end, base_price)
            else: # Per Usage
                amount = float(tool.price_per_use) if tool.price_per_use else 0.0
            
            usage_event.amount = amount
            session.add(usage_event)
            count += 1
            print(f"  -> Created UsageEvent {usage_event.id} with amount: {amount}")
            
        await session.commit()
        print(f"Synchronization complete. Created {count} usage events.")

if __name__ == "__main__":
    asyncio.run(sync_usage_from_reservations())
