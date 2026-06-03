from datetime import datetime
from typing import List, Optional
from decimal import Decimal

from sqlalchemy import insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import (
    Account,
    AccountMembershipChangeRequest,
    AccountType,
    account_members,
)
from app.models.project import Project
from app.models.project import ProjectJoinRequest
from app.models.user import User
from app.schemas.account import (
    AccountCreate,
    AccountMembershipChangeRequestStatus,
    AccountTypeCreate,
    AccountTypeUpdate,
    AccountUpdate,
)

class AccountProjectBindingError(Exception):
    """Raised when project-account binding violates business rules."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class AccountMembershipChangeRequestError(Exception):
    """Raised when membership change request validation or review fails."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class AccountService:
    """账户服务"""

    @staticmethod
    def _is_locked_security_external_project(project: Optional[Project]) -> bool:
        if not project:
            return False
        identifier = str(getattr(project, "application_identifier", "") or "").strip()
        return identifier.startswith("security-server:") and bool(
            getattr(project, "allow_external_booking_request", False)
        )

    @staticmethod
    async def _is_internal_account_type(db: AsyncSession, type_id: Optional[int]) -> bool:
        if type_id is None:
            return False
        account_type = await db.get(AccountType, type_id)
        if not account_type or not account_type.name:
            return False
        raw_name = account_type.name.strip()
        lowered = raw_name.lower()
        return ("internal" in lowered) or ("内部" in raw_name)

    @staticmethod
    def _is_internal_account_type_name(type_name: Optional[str]) -> bool:
        if not type_name:
            return False
        raw_name = type_name.strip()
        lowered = raw_name.lower()
        return ("internal" in lowered) or ("内部" in raw_name)

    @staticmethod
    def _is_manual_membership_org_account(account: Optional[Account]) -> bool:
        if not account or account.user_id is not None or not account.active:
            return False
        type_name = account.type.name if getattr(account, "type", None) else None
        return not AccountService._is_internal_account_type_name(type_name)

    @staticmethod
    async def _get_project_bound_to_account(
        db: AsyncSession, account_id: int
    ) -> Optional[Project]:
        return await db.scalar(
            select(Project).where(Project.account_id == account_id).order_by(Project.id)
        )

    @staticmethod
    async def _ensure_account_not_locked_for_lifecycle_change(
        db: AsyncSession, account_id: int
    ) -> None:
        bound_project = await AccountService._get_project_bound_to_account(db, account_id)
        if AccountService._is_locked_security_external_project(bound_project):
            raise AccountProjectBindingError(
                "该所属账户已绑定对外开放项目，不能停用或删除"
            )

    @staticmethod
    async def _attach_default_project_metadata(
        db: AsyncSession,
        accounts: List[Account],
    ) -> None:
        if not accounts:
            return
        account_ids = [int(account.id) for account in accounts if getattr(account, "id", None) is not None]
        if not account_ids:
            return

        rows = await db.execute(
            select(
                Project.id,
                Project.name,
                Project.external_display_name,
                Project.account_id,
                Project.application_identifier,
                Project.allow_external_booking_request,
            ).where(Project.account_id.in_(account_ids))
        )

        by_account_id: dict[int, tuple[int, str, bool]] = {}
        for project_id, name, external_display_name, account_id, application_identifier, external_visible in rows.all():
            if account_id is None:
                continue
            display_name = str((external_display_name or name or "")).strip() or str(name or "")
            is_locked = str(application_identifier or "").strip().startswith("security-server:") and bool(
                external_visible
            )
            by_account_id[int(account_id)] = (int(project_id), display_name, is_locked)

        for account in accounts:
            payload = by_account_id.get(int(account.id))
            if payload is None:
                setattr(account, "default_project_id", None)
                setattr(account, "default_project_name", None)
                setattr(account, "project_binding_locked", False)
                continue
            project_id, project_name, is_locked = payload
            setattr(account, "default_project_id", project_id)
            setattr(account, "default_project_name", project_name)
            setattr(account, "project_binding_locked", is_locked)

    @staticmethod
    async def _bind_account_to_project(
        db: AsyncSession,
        account_id: int,
        project_id: int,
    ) -> None:
        target_project = await db.get(Project, project_id)
        if not target_project:
            raise AccountProjectBindingError("关联项目不存在")

        if target_project.account_id is not None and target_project.account_id != account_id:
            raise AccountProjectBindingError(
                f"项目“{target_project.name}”已绑定到其他账户"
            )

        existing_project = await db.scalar(
            select(Project).where(
                Project.account_id == account_id,
                Project.id != project_id,
            )
        )
        if existing_project:
            existing_project.account_id = None

        target_project.account_id = account_id

    @staticmethod
    async def _clear_project_binding(db: AsyncSession, account_id: int) -> None:
        result = await db.execute(select(Project).where(Project.account_id == account_id))
        for project in list(result.scalars().all()):
            project.account_id = None

    @staticmethod
    async def get_or_create_user_account(db: AsyncSession, user: User) -> Optional[Account]:
        """Lookup the legacy personal account bound to a user, if any.

        Personal accounts are deprecated and no longer auto-created. This function
        is retained only to surface pre-existing legacy rows where ``account.user_id == user.id``;
        callers must handle ``None``.
        """
        return await db.scalar(select(Account).where(Account.user_id == user.id))

    @staticmethod
    async def resolve_payer_account_for_user(
        db: AsyncSession,
        user_id: int,
        *,
        preferred_account_id: Optional[int] = None,
        require_reservable: bool = False,
    ) -> Optional[Account]:
        """Resolve a payer account for a reservation/usage user.

        Priority:
        1) `preferred_account_id` if provided and user can access it
        2) shared organization account(s) the user belongs to (sorted by id)
        """
        accounts = [
            account
            for account in await AccountService.get_accounts_for_user(
                db,
                user_id,
                skip=0,
                limit=1000,
                active=True,
            )
            if account.user_id is None
        ]
        by_id = {int(account.id): account for account in accounts}

        if preferred_account_id is not None:
            preferred = by_id.get(int(preferred_account_id))
            if preferred is None:
                return None
            if require_reservable and not await AccountService.account_can_reserve(db, preferred.id):
                return None
            return preferred

        candidates = sorted(accounts, key=lambda account: int(account.id))

        if require_reservable:
            for account in candidates:
                if await AccountService.account_can_reserve(db, account.id):
                    return account
            return None

        return candidates[0] if candidates else None

    @staticmethod
    async def account_can_reserve(db: AsyncSession, account_id: int) -> bool:
        """Whether an account is allowed to create new reservations based on funds."""
        row = (
            await db.execute(
                select(Account.balance, Account.credit_limit).where(Account.id == account_id)
            )
        ).first()
        if not row:
            return False
        balance_val, credit_limit_val = row
        balance = Decimal(str(balance_val or 0))
        credit_limit = Decimal(str(credit_limit_val or 0))
        return balance > 0 or credit_limit > 0

    @staticmethod
    async def account_has_project_access_for_user(
        db: AsyncSession,
        *,
        user_id: int,
        project_id: int,
        account: Optional[Account] = None,
        account_id: Optional[int] = None,
    ) -> bool:
        if account is None:
            if account_id is None:
                return False
            account = await AccountService.get_account(db, account_id)
        if account is None:
            return False

        account_owner_id = getattr(account, "user_id", None)
        member_ids = list(getattr(account, "member_ids", []) or [])
        if account_owner_id != user_id and user_id not in member_ids:
            return False

        if account_owner_id is not None:
            return int(account_owner_id) == int(user_id)

        source_project_id = getattr(account, "default_project_id", None)
        if source_project_id is None:
            bound_project = await AccountService._get_project_bound_to_account(db, int(account.id))
            source_project_id = bound_project.id if bound_project else None

        if source_project_id is not None and int(source_project_id) == int(project_id):
            return True

        if source_project_id is None:
            # 未绑定任何项目的共享账户视为通用账户：成员可在任意项目使用。
            # 与"消灭个人账户"迁移前 personal account 的语义保持一致——
            # 那时的 personal account 也没有项目约束，迁移成共享后保留这一特权。
            return True

        approved_request = await db.scalar(
            select(ProjectJoinRequest.id).where(
                ProjectJoinRequest.requester_user_id == user_id,
                ProjectJoinRequest.source_project_id == source_project_id,
                ProjectJoinRequest.target_project_id == project_id,
                ProjectJoinRequest.status == "APPROVED",
            )
        )
        return approved_request is not None

    @staticmethod
    async def get_reservable_accounts_for_user(
        db: AsyncSession,
        user_id: int,
        project_id: int,
        *,
        skip: int = 0,
        limit: int = 100,
        active: Optional[bool] = None,
        type_id: Optional[int] = None,
    ) -> List[Account]:
        fetch_limit = max(skip + limit, 1000)
        accounts = await AccountService.get_accounts_for_user(
            db,
            user_id,
            skip=0,
            limit=fetch_limit,
            active=active,
            type_id=type_id,
        )
        allowed_accounts: List[Account] = []
        for account in accounts:
            if account.user_id is not None:
                continue
            if await AccountService.account_has_project_access_for_user(
                db,
                user_id=user_id,
                project_id=project_id,
                account=account,
            ):
                allowed_accounts.append(account)
        return allowed_accounts[skip:skip + limit]

    @staticmethod
    async def resolve_reservable_account_for_user(
        db: AsyncSession,
        user_id: int,
        *,
        project_id: int,
        preferred_account_id: Optional[int] = None,
        require_reservable: bool = False,
    ) -> Optional[Account]:
        accounts = await AccountService.get_reservable_accounts_for_user(
            db,
            user_id,
            project_id,
            skip=0,
            limit=1000,
            active=True,
        )
        by_id = {int(account.id): account for account in accounts}

        if preferred_account_id is not None:
            preferred = by_id.get(int(preferred_account_id))
            if preferred is None:
                return None
            if require_reservable and not await AccountService.account_can_reserve(db, preferred.id):
                return None
            return preferred

        candidates = sorted(accounts, key=lambda account: int(account.id))

        if require_reservable:
            for account in candidates:
                if await AccountService.account_can_reserve(db, account.id):
                    return account
            return None

        return candidates[0] if candidates else None

    @staticmethod
    async def consume_balance_or_credit(db: AsyncSession, account_id: int, amount: Decimal) -> Optional[Account]:
        """Consume account balance first, then credit_limit if balance is insufficient.

        This is used to implement:
        - 余额为 0 时扣信用额度
        - 信用额度耗尽后无法预约
        """
        try:
            amt = Decimal(str(amount or 0))
        except Exception:
            amt = Decimal("0")
        if amt <= 0:
            return await AccountService.get_account(db, account_id)

        account = await db.get(Account, account_id)
        if not account:
            return None

        balance = Decimal(str(account.balance or 0))
        credit_limit = Decimal(str(account.credit_limit or 0))

        if balance >= amt:
            account.balance = balance - amt
        else:
            remaining = amt - balance
            account.balance = Decimal("0")
            account.credit_limit = credit_limit - remaining

        return account

    @staticmethod
    async def refund_balance_or_credit(db: AsyncSession, account_id: int, amount: Decimal) -> Optional[Account]:
        """Refund funds back to an account.

        For simplicity we "repay" any negative credit_limit first, then top up balance.
        This keeps the account usable again after waiving previously validated charges.
        """
        try:
            amt = Decimal(str(amount or 0))
        except Exception:
            amt = Decimal("0")
        if amt <= 0:
            return await AccountService.get_account(db, account_id)

        account = await db.get(Account, account_id)
        if not account:
            return None

        balance = Decimal(str(account.balance or 0))
        credit_limit = Decimal(str(account.credit_limit or 0))

        # If credit has been over-consumed (negative), repay it first.
        if credit_limit < 0:
            repay = min(amt, -credit_limit)
            account.credit_limit = credit_limit + repay
            amt -= repay

        if amt > 0:
            account.balance = balance + amt

        return account

    @staticmethod
    async def get_account_types(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[AccountType]:
        """获取账户类型列表"""
        result = await db.execute(
            select(AccountType)
            .order_by(AccountType.display_order, AccountType.name)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_account_type(db: AsyncSession, type_id: int) -> Optional[AccountType]:
        """获取单个账户类型"""
        result = await db.execute(
            select(AccountType).where(AccountType.id == type_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_account_type(
        db: AsyncSession,
        account_type_data: AccountTypeCreate
    ) -> AccountType:
        """创建账户类型"""
        account_type = AccountType(**account_type_data.model_dump())
        db.add(account_type)
        await db.commit()
        await db.refresh(account_type)
        return account_type

    @staticmethod
    async def update_account_type(
        db: AsyncSession,
        type_id: int,
        account_type_data: AccountTypeUpdate
    ) -> Optional[AccountType]:
        """更新账户类型"""
        result = await db.execute(
            select(AccountType).where(AccountType.id == type_id)
        )
        account_type = result.scalar_one_or_none()
        
        if not account_type:
            return None
        
        update_data = account_type_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(account_type, field, value)
        
        await db.commit()
        await db.refresh(account_type)
        return account_type

    @staticmethod
    async def delete_account_type(db: AsyncSession, type_id: int) -> bool:
        """删除账户类型"""
        result = await db.execute(
            select(AccountType).where(AccountType.id == type_id)
        )
        account_type = result.scalar_one_or_none()
        
        if not account_type:
            return False
        
        await db.delete(account_type)
        await db.commit()
        return True

    @staticmethod
    async def get_accounts(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        active: Optional[bool] = None,
        type_id: Optional[int] = None,
    ) -> List[Account]:
        """获取账户列表"""
        query = select(Account).options(
            selectinload(Account.type),
            selectinload(Account.members),
        )

        if active is not None:
            query = query.where(Account.active == active)

        if type_id is not None:
            query = query.where(Account.type_id == type_id)
        
        query = query.order_by(Account.name).offset(skip).limit(limit)
        
        result = await db.execute(query)
        accounts = list(result.scalars().all())
        await AccountService._attach_default_project_metadata(db, accounts)
        return accounts

    @staticmethod
    async def get_accounts_for_user(
        db: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        active: Optional[bool] = None,
        type_id: Optional[int] = None,
    ) -> List[Account]:
        """获取与用户相关的账户（个人账户 + 共享账户）"""
        query = (
            select(Account)
            .options(
                selectinload(Account.type),
                selectinload(Account.members),
            )
            .outerjoin(account_members, Account.id == account_members.c.account_id)
            .where(
                or_(
                    Account.user_id == user_id,
                    account_members.c.user_id == user_id,
                )
            )
        )

        if active is not None:
            query = query.where(Account.active == active)

        if type_id is not None:
            query = query.where(Account.type_id == type_id)

        query = query.order_by(Account.name).offset(skip).limit(limit)
        result = await db.execute(query)
        accounts = list(result.scalars().all())
        await AccountService._attach_default_project_metadata(db, accounts)
        return accounts

    @staticmethod
    async def get_account(db: AsyncSession, account_id: int) -> Optional[Account]:
        """获取单个账户"""
        result = await db.execute(
            select(Account)
            .options(
                selectinload(Account.type),
                selectinload(Account.projects),
                selectinload(Account.members),
            )
            .where(Account.id == account_id)
        )
        account = result.scalar_one_or_none()
        if account:
            await AccountService._attach_default_project_metadata(db, [account])
        return account

    @staticmethod
    async def get_account_by_name(db: AsyncSession, name: str) -> Optional[Account]:
        """根据名称获取账户"""
        result = await db.execute(
            select(Account).where(Account.name == name)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_account(
        db: AsyncSession,
        account_data: AccountCreate
    ) -> Account:
        """创建账户"""
        create_data = account_data.model_dump(exclude={"member_ids", "project_id"})
        account = Account(**create_data)
        db.add(account)
        await db.flush()

        member_ids = list(dict.fromkeys(account_data.member_ids or []))
        requires_project_binding = (
            account.user_id is None
            and await AccountService._is_internal_account_type(db, account.type_id)
        )
        if requires_project_binding and member_ids:
            raise AccountProjectBindingError(
                "内部组织账户成员由项目归属自动维护，不能手动设置"
            )

        if member_ids:
            result = await db.execute(select(User).where(User.id.in_(member_ids)))
            account.members = list(result.scalars().all())

        if requires_project_binding:
            if account_data.project_id is None:
                raise AccountProjectBindingError(
                    "内部组织账户必须绑定且只能绑定一个项目"
                )
            await AccountService._bind_account_to_project(db, account.id, account_data.project_id)
        elif account_data.project_id is not None:
            raise AccountProjectBindingError(
                "只有内部组织账户可以绑定项目"
            )

        await db.commit()
        loaded = await AccountService.get_account(db, account.id)
        return loaded or account

    @staticmethod
    async def update_account(
        db: AsyncSession,
        account_id: int,
        account_data: AccountUpdate
    ) -> Optional[Account]:
        """更新账户"""
        # NOTE: In async SQLAlchemy, assigning relationship collections requires the collection
        # to be eagerly loaded; otherwise SQLAlchemy may attempt a lazy-load and raise MissingGreenlet.
        result = await db.execute(
            select(Account)
            .options(selectinload(Account.members))
            .where(Account.id == account_id)
        )
        account = result.scalar_one_or_none()
        
        if not account:
            return None
        
        full_update_data = account_data.model_dump(exclude_unset=True)
        project_field_provided = "project_id" in full_update_data
        next_user_id = (
            full_update_data["user_id"] if "user_id" in full_update_data else account.user_id
        )
        next_type_id = (
            full_update_data["type_id"] if "type_id" in full_update_data else account.type_id
        )
        bound_project = await AccountService._get_project_bound_to_account(db, account_id)
        project_binding_locked = AccountService._is_locked_security_external_project(bound_project)
        requires_project_binding = (
            next_user_id is None
            and await AccountService._is_internal_account_type(db, next_type_id)
        )
        if project_binding_locked:
            if next_user_id is not None:
                raise AccountProjectBindingError(
                    "该账户已绑定对外开放项目，必须保持为组织账户"
                )
            if project_field_provided:
                if bound_project is None or account_data.project_id is None:
                    raise AccountProjectBindingError(
                        "该账户的默认项目关联为只读，不可修改"
                    )
                if int(account_data.project_id) != int(bound_project.id):
                    raise AccountProjectBindingError(
                        "该账户的默认项目关联为只读，不可修改"
                    )
        if requires_project_binding:
            disallowed_fields = set(full_update_data.keys()) - {"balance"}
            if disallowed_fields:
                raise AccountProjectBindingError(
                    "内部组织账户当前只允许修改余额"
                )
            if account_data.member_ids is not None:
                raise AccountProjectBindingError(
                    "内部组织账户成员由项目归属自动维护，不能手动设置"
                )

        update_data = account_data.model_dump(
            exclude_unset=True, exclude={"member_ids", "project_id"}
        )
        for field, value in update_data.items():
            setattr(account, field, value)

        if not requires_project_binding and account_data.member_ids is not None:
            member_ids = list(dict.fromkeys(account_data.member_ids))
            if member_ids:
                result = await db.execute(select(User).where(User.id.in_(member_ids)))
                account.members = list(result.scalars().all())
            else:
                account.members = []

        if requires_project_binding:
            target_project_id: Optional[int] = None
            if project_field_provided:
                target_project_id = account_data.project_id
            else:
                bound_project = await AccountService._get_project_bound_to_account(db, account_id)
                target_project_id = bound_project.id if bound_project else None

            if target_project_id is None:
                raise AccountProjectBindingError(
                    "内部组织账户必须绑定且只能绑定一个项目"
                )
            await AccountService._bind_account_to_project(db, account_id, target_project_id)
        else:
            if project_binding_locked:
                # Keep existing locked binding unchanged.
                pass
            else:
                if project_field_provided and account_data.project_id is not None:
                    raise AccountProjectBindingError(
                        "只有内部组织账户可以绑定项目"
                    )
                await AccountService._clear_project_binding(db, account_id)
        
        await db.commit()
        loaded = await AccountService.get_account(db, account_id)
        return loaded or account

    @staticmethod
    async def get_account_members(db: AsyncSession, account_id: int) -> Optional[List[User]]:
        account = await AccountService.get_account(db, account_id)
        if not account:
            return None
        return list(account.members)

    @staticmethod
    async def user_is_account_member(db: AsyncSession, account_id: int, user_id: int) -> bool:
        result = await db.execute(
            select(account_members.c.account_id).where(
                account_members.c.account_id == account_id,
                account_members.c.user_id == user_id,
            )
        )
        return result.first() is not None

    @staticmethod
    async def set_account_members(
        db: AsyncSession,
        account_id: int,
        member_ids: List[int],
    ) -> Optional[Account]:
        account = await AccountService.get_account(db, account_id)
        if not account:
            return None

        is_internal_org_account = (
            account.user_id is None
            and await AccountService._is_internal_account_type(db, account.type_id)
        )
        if is_internal_org_account:
            raise AccountProjectBindingError(
                "内部组织账户成员由项目归属自动维护，不能手动设置"
            )

        normalized_member_ids = list(dict.fromkeys(member_ids))
        if normalized_member_ids:
            result = await db.execute(select(User).where(User.id.in_(normalized_member_ids)))
            account.members = list(result.scalars().all())
        else:
            account.members = []
        await db.commit()
        return await AccountService.get_account(db, account_id)

    @staticmethod
    async def _get_current_shared_account_for_user(
        db: AsyncSession, user_id: int
    ) -> Optional[Account]:
        result = await db.execute(
            select(Account)
            .options(selectinload(Account.type), selectinload(Account.members))
            .join(account_members, Account.id == account_members.c.account_id)
            .where(account_members.c.user_id == user_id)
            .order_by(Account.id)
        )
        return result.scalars().first()

    @staticmethod
    def _membership_change_request_query():
        return (
            select(AccountMembershipChangeRequest)
            .options(
                selectinload(AccountMembershipChangeRequest.requester),
                selectinload(AccountMembershipChangeRequest.reviewer),
                selectinload(AccountMembershipChangeRequest.source_account).selectinload(Account.type),
                selectinload(AccountMembershipChangeRequest.target_account).selectinload(Account.type),
            )
        )

    @staticmethod
    async def _get_membership_change_request(
        db: AsyncSession, request_id: int
    ) -> Optional[AccountMembershipChangeRequest]:
        result = await db.execute(
            AccountService._membership_change_request_query().where(
                AccountMembershipChangeRequest.id == request_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_joinable_organization_accounts(db: AsyncSession) -> List[Account]:
        result = await db.execute(
            select(Account)
            .options(selectinload(Account.type), selectinload(Account.members))
            .where(Account.user_id.is_(None), Account.active.is_(True))
            .order_by(Account.name)
        )
        accounts = list(result.scalars().all())
        return [account for account in accounts if AccountService._is_manual_membership_org_account(account)]

    @staticmethod
    async def list_membership_change_requests_for_user(
        db: AsyncSession,
        user_id: int,
        *,
        status: Optional[AccountMembershipChangeRequestStatus] = None,
        limit: int = 20,
    ) -> List[AccountMembershipChangeRequest]:
        query = AccountService._membership_change_request_query().where(
            AccountMembershipChangeRequest.requester_user_id == user_id
        )
        if status is not None:
            query = query.where(AccountMembershipChangeRequest.status == status.value)
        query = query.order_by(AccountMembershipChangeRequest.created_at.desc()).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def list_membership_change_requests(
        db: AsyncSession,
        *,
        status: Optional[AccountMembershipChangeRequestStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AccountMembershipChangeRequest]:
        query = AccountService._membership_change_request_query()
        if status is not None:
            query = query.where(AccountMembershipChangeRequest.status == status.value)
        query = (
            query.order_by(AccountMembershipChangeRequest.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create_membership_change_request(
        db: AsyncSession,
        *,
        requester_user: User,
        target_account_id: int,
        reason: Optional[str] = None,
    ) -> AccountMembershipChangeRequest:
        pending = await db.scalar(
            select(AccountMembershipChangeRequest).where(
                AccountMembershipChangeRequest.requester_user_id == requester_user.id,
                AccountMembershipChangeRequest.status
                == AccountMembershipChangeRequestStatus.PENDING.value,
            )
        )
        if pending:
            raise AccountMembershipChangeRequestError(
                "你已有一条待审批的所属账户加入申请"
            )

        target_result = await db.execute(
            select(Account)
            .options(selectinload(Account.type), selectinload(Account.members))
            .where(Account.id == target_account_id)
        )
        target_account = target_result.scalar_one_or_none()
        if not target_account:
            raise AccountMembershipChangeRequestError("目标所属账户不存在")
        if target_account.user_id is not None:
            raise AccountMembershipChangeRequestError("目标账户必须是组织账户")
        if not target_account.active:
            raise AccountMembershipChangeRequestError("目标所属账户已停用")
        if not AccountService._is_manual_membership_org_account(target_account):
            raise AccountMembershipChangeRequestError(
                "目标所属账户不支持手动成员变更"
            )

        already_joined = await AccountService.user_is_account_member(
            db,
            target_account.id,
            requester_user.id,
        )
        if already_joined:
            raise AccountMembershipChangeRequestError(
                "你已经属于该所属账户"
            )

        membership_request = AccountMembershipChangeRequest(
            requester_user_id=requester_user.id,
            source_account_id=None,
            target_account_id=target_account.id,
            status=AccountMembershipChangeRequestStatus.PENDING.value,
            reason=(reason or "").strip() or None,
        )
        db.add(membership_request)
        await db.commit()
        loaded = await AccountService._get_membership_change_request(db, membership_request.id)
        return loaded or membership_request

    @staticmethod
    async def cancel_membership_change_request(
        db: AsyncSession,
        *,
        request_id: int,
        requester_user: User,
    ) -> Optional[AccountMembershipChangeRequest]:
        membership_request = await AccountService._get_membership_change_request(db, request_id)
        if not membership_request:
            return None
        if membership_request.requester_user_id != requester_user.id:
            raise AccountMembershipChangeRequestError("只能撤销自己的申请")
        if membership_request.status != AccountMembershipChangeRequestStatus.PENDING.value:
            raise AccountMembershipChangeRequestError("只有待审批申请才能撤销")

        membership_request.status = AccountMembershipChangeRequestStatus.CANCELLED.value
        membership_request.reviewer_user_id = None
        membership_request.review_comment = None
        membership_request.reviewed_at = None
        membership_request.updated_at = datetime.utcnow()
        await db.commit()
        loaded = await AccountService._get_membership_change_request(db, request_id)
        return loaded or membership_request

    @staticmethod
    async def approve_membership_change_request(
        db: AsyncSession,
        *,
        request_id: int,
        reviewer_user: User,
        comment: Optional[str] = None,
    ) -> Optional[AccountMembershipChangeRequest]:
        membership_request = await AccountService._get_membership_change_request(db, request_id)
        if not membership_request:
            return None
        if membership_request.status != AccountMembershipChangeRequestStatus.PENDING.value:
            raise AccountMembershipChangeRequestError("只有待审批申请才能通过")
        if membership_request.target_account_id is None:
            raise AccountMembershipChangeRequestError("目标所属账户已不存在")

        target_result = await db.execute(
            select(Account).options(selectinload(Account.type)).where(
                Account.id == membership_request.target_account_id
            )
        )
        target_account = target_result.scalar_one_or_none()
        if not target_account:
            raise AccountMembershipChangeRequestError("目标所属账户不存在")
        if target_account.user_id is not None:
            raise AccountMembershipChangeRequestError("目标账户不是组织账户")
        if not target_account.active:
            raise AccountMembershipChangeRequestError("目标所属账户已停用")
        if not AccountService._is_manual_membership_org_account(target_account):
            raise AccountMembershipChangeRequestError(
                "目标所属账户不支持手动成员变更"
            )

        existing_membership = await db.scalar(
            select(account_members.c.account_id).where(
                account_members.c.account_id == target_account.id,
                account_members.c.user_id == membership_request.requester_user_id
            )
        )

        if existing_membership is None:
            await db.execute(
                insert(account_members).values(
                    account_id=target_account.id,
                    user_id=membership_request.requester_user_id,
                )
            )

        membership_request.status = AccountMembershipChangeRequestStatus.APPROVED.value
        membership_request.reviewer_user_id = reviewer_user.id
        membership_request.review_comment = (comment or "").strip() or None
        membership_request.reviewed_at = datetime.utcnow()
        membership_request.updated_at = datetime.utcnow()

        await db.commit()
        loaded = await AccountService._get_membership_change_request(db, request_id)
        return loaded or membership_request

    @staticmethod
    async def reject_membership_change_request(
        db: AsyncSession,
        *,
        request_id: int,
        reviewer_user: User,
        comment: Optional[str] = None,
    ) -> Optional[AccountMembershipChangeRequest]:
        membership_request = await AccountService._get_membership_change_request(db, request_id)
        if not membership_request:
            return None
        if membership_request.status != AccountMembershipChangeRequestStatus.PENDING.value:
            raise AccountMembershipChangeRequestError("只有待审批申请才能驳回")

        membership_request.status = AccountMembershipChangeRequestStatus.REJECTED.value
        membership_request.reviewer_user_id = reviewer_user.id
        membership_request.review_comment = (comment or "").strip() or None
        membership_request.reviewed_at = datetime.utcnow()
        membership_request.updated_at = datetime.utcnow()

        await db.commit()
        loaded = await AccountService._get_membership_change_request(db, request_id)
        return loaded or membership_request

    @staticmethod
    async def delete_account(db: AsyncSession, account_id: int) -> bool:
        """删除账户"""
        result = await db.execute(
            select(Account).where(Account.id == account_id)
        )
        account = result.scalar_one_or_none()
        
        if not account:
            return False

        await AccountService._ensure_account_not_locked_for_lifecycle_change(
            db, account_id
        )
        
        await db.delete(account)
        await db.commit()
        return True

    @staticmethod
    async def activate_account(db: AsyncSession, account_id: int) -> Optional[Account]:
        """激活账户"""
        result = await db.execute(
            select(Account).where(Account.id == account_id)
        )
        account = result.scalar_one_or_none()
        
        if not account:
            return None
        
        account.active = True
        await db.commit()
        loaded = await AccountService.get_account(db, account_id)
        return loaded or account

    @staticmethod
    async def deactivate_account(db: AsyncSession, account_id: int) -> Optional[Account]:
        """停用账户"""
        result = await db.execute(
            select(Account).where(Account.id == account_id)
        )
        account = result.scalar_one_or_none()
        
        if not account:
            return None

        await AccountService._ensure_account_not_locked_for_lifecycle_change(
            db, account_id
        )
        
        account.active = False
        await db.commit()
        loaded = await AccountService.get_account(db, account_id)
        return loaded or account
