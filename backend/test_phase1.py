"""
快速测试脚本 - 验证 Phase 1 实现

运行前请确保：
1. cd backend
2. pip install -r requirements.txt
3. python main.py（在另一个终端）
4. python test_phase1.py
"""

import asyncio
import httpx
from datetime import datetime

BASE_URL = "http://localhost:8000/api"

# 测试用户凭证（需要先创建）
TEST_USER = {
    "username": "testuser",
    "password": "testpass123"
}


async def test_authentication():
    """测试认证"""
    print("\n=== 测试认证 ===")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/auth/login",
            data=TEST_USER
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            print(f"✅ 登录成功！Token: {token[:20]}...")
            return token
        else:
            print(f"❌ 登录失败: {response.text}")
            return None


async def test_accounts(token: str):
    """测试账户 API"""
    print("\n=== 测试账户系统 ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        # 创建账户类型
        print("1. 创建账户类型...")
        response = await client.post(
            f"{BASE_URL}/accounts/account-types",
            json={"name": "Research", "display_order": 1},
            headers=headers
        )
        print(f"   状态: {response.status_code}")
        
        # 创建账户
        print("2. 创建账户...")
        response = await client.post(
            f"{BASE_URL}/accounts/accounts",
            json={
                "name": "Test Account",
                "note": "测试账户",
                "active": True
            },
            headers=headers
        )
        if response.status_code == 201:
            account_id = response.json()["id"]
            print(f"   ✅ 账户创建成功！ID: {account_id}")
            
            # 获取账户列表
            print("3. 获取账户列表...")
            response = await client.get(
                f"{BASE_URL}/accounts/accounts",
                headers=headers
            )
            accounts = response.json()
            print(f"   ✅ 找到 {len(accounts)} 个账户")
            
            # 停用账户
            print("4. 停用账户...")
            response = await client.post(
                f"{BASE_URL}/accounts/accounts/{account_id}/deactivate",
                headers=headers
            )
            print(f"   状态: {response.status_code}")
            
            return account_id
        else:
            print(f"   ❌ 创建失败: {response.text}")
            return None


async def test_usage_events(token: str, tool_id: int = 1, user_id: int = 1):
    """测试使用记录 API"""
    print("\n=== 测试使用记录系统 ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        # 开始使用工具
        print("1. 开始使用工具...")
        response = await client.post(
            f"{BASE_URL}/usage/usage-events",
            json={
                "user_id": user_id,
                "operator_id": user_id,
                "project_id": 1,
                "tool_id": tool_id,
                "note": "测试使用"
            },
            headers=headers
        )
        if response.status_code == 201:
            event_id = response.json()["id"]
            print(f"   ✅ 使用记录创建成功！ID: {event_id}")
            
            # 获取进行中的使用记录
            print("2. 获取进行中的使用记录...")
            response = await client.get(
                f"{BASE_URL}/usage/usage-events?in_progress_only=true",
                headers=headers
            )
            events = response.json()
            print(f"   ✅ 找到 {len(events)} 个进行中的记录")
            
            # 结束使用
            print("3. 结束使用...")
            await asyncio.sleep(2)  # 等待2秒
            response = await client.post(
                f"{BASE_URL}/usage/usage-events/{event_id}/end",
                json={"run_data": '{"result": "success"}'},
                headers=headers
            )
            if response.status_code == 200:
                duration = response.json().get("end")
                print(f"   ✅ 使用结束！结束时间: {duration}")
            
            # 获取使用统计
            print("4. 获取使用统计...")
            response = await client.get(
                f"{BASE_URL}/usage/usage-events/stats",
                headers=headers
            )
            if response.status_code == 200:
                stats = response.json()
                print(f"   ✅ 总使用次数: {stats['total_count']}")
                print(f"   ✅ 总时长: {stats['total_duration_minutes']} 分钟")
            
            return event_id
        else:
            print(f"   ❌ 创建失败: {response.text}")
            return None


async def test_tasks(token: str, tool_id: int = 1):
    """测试任务 API"""
    print("\n=== 测试任务系统 ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        # 创建任务分类
        print("1. 创建任务分类...")
        response = await client.post(
            f"{BASE_URL}/tasks/task-categories",
            json={"name": "维护", "stage": 0},
            headers=headers
        )
        print(f"   状态: {response.status_code}")
        
        # 创建任务
        print("2. 创建任务...")
        response = await client.post(
            f"{BASE_URL}/tasks/tasks",
            json={
                "tool_id": tool_id,
                "urgency": 1,  # HIGH
                "force_shutdown": True,
                "safety_hazard": True,
                "problem_description": "工具需要紧急维护"
            },
            headers=headers
        )
        if response.status_code == 201:
            task_id = response.json()["id"]
            print(f"   ✅ 任务创建成功！ID: {task_id}")
            
            # 获取任务列表
            print("3. 获取开放任务列表...")
            response = await client.get(
                f"{BASE_URL}/tasks/tasks?open_only=true",
                headers=headers
            )
            tasks = response.json()
            print(f"   ✅ 找到 {len(tasks)} 个开放任务")
            
            # 获取紧急任务
            print("4. 获取紧急任务...")
            response = await client.get(
                f"{BASE_URL}/tasks/tasks/urgent",
                headers=headers
            )
            urgent_tasks = response.json()
            print(f"   ✅ 找到 {len(urgent_tasks)} 个紧急任务")
            
            # 更新任务
            print("5. 更新任务进度...")
            response = await client.put(
                f"{BASE_URL}/tasks/tasks/{task_id}",
                json={
                    "progress_description": "正在检查工具状态..."
                },
                headers=headers
            )
            print(f"   状态: {response.status_code}")
            
            # 解决任务
            print("6. 解决任务...")
            response = await client.post(
                f"{BASE_URL}/tasks/tasks/{task_id}/resolve",
                json={
                    "resolution_description": "已完成维护，工具恢复正常"
                },
                headers=headers
            )
            if response.status_code == 200:
                print(f"   ✅ 任务已解决！")
            
            # 获取任务历史
            print("7. 获取任务历史...")
            response = await client.get(
                f"{BASE_URL}/tasks/tasks/{task_id}/history",
                headers=headers
            )
            history = response.json()
            print(f"   ✅ 找到 {len(history)} 条历史记录")
            
            return task_id
        else:
            print(f"   ❌ 创建失败: {response.text}")
            return None


async def main():
    """主测试函数"""
    print("=" * 60)
    print("Phase 1 功能测试")
    print("=" * 60)
    
    # 1. 认证
    token = await test_authentication()
    if not token:
        print("\n❌ 认证失败，请先创建测试用户")
        print("提示: 使用 /api/users 端点创建用户")
        return
    
    # 2. 测试账户系统
    account_id = await test_accounts(token)
    
    # 3. 测试使用记录系统
    event_id = await test_usage_events(token)
    
    # 4. 测试任务系统
    task_id = await test_tasks(token)
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print(f"\n创建的资源 ID:")
    print(f"  账户: {account_id}")
    print(f"  使用记录: {event_id}")
    print(f"  任务: {task_id}")
    print("\n请访问 http://localhost:8000/api/docs 查看完整 API 文档")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n测试中断")
    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
        print("\n请确保:")
        print("1. FastAPI 服务正在运行 (python main.py)")
        print("2. 已创建测试用户")
        print("3. 数据库连接正常")
