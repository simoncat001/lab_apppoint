import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.verification_code import VerificationCode


class VerificationServiceError(Exception):
    """Raised when a verification-code request is rejected by rate limits."""

    def __init__(self, message: str, status_code: int = 429):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# Per-target throttling for code issuance. The verify path consumes the code on
# any attempt (right or wrong), so the only remaining brute-force surface is
# repeatedly triggering new codes — which these limits cap.
_MIN_RESEND_INTERVAL_SECONDS = 60
_MAX_CODES_PER_HOUR = 5


class VerificationService:
    @staticmethod
    def generate_code() -> str:
        return f"{secrets.randbelow(900000) + 100000}"

    @staticmethod
    async def create_code(
        db: AsyncSession,
        target: str,
        code_type: str,
        purpose: str,
    ) -> VerificationCode:
        now = datetime.utcnow()

        # Throttle: minimum interval between consecutive sends to the same target/purpose.
        last_sent_row = await db.execute(
            select(VerificationCode.created_at)
            .where(
                VerificationCode.target == target,
                VerificationCode.type == code_type,
                VerificationCode.purpose == purpose,
            )
            .order_by(VerificationCode.created_at.desc())
            .limit(1)
        )
        last_sent_at = last_sent_row.scalar_one_or_none()
        if last_sent_at is not None:
            elapsed = (now - last_sent_at).total_seconds()
            if elapsed < _MIN_RESEND_INTERVAL_SECONDS:
                wait = int(_MIN_RESEND_INTERVAL_SECONDS - elapsed) + 1
                raise VerificationServiceError(
                    f"请等待 {wait} 秒后再请求验证码",
                    status_code=429,
                )

        # Throttle: hard cap on issuance per target within a rolling hour.
        hourly_window_start = now - timedelta(hours=1)
        hourly_count_row = await db.execute(
            select(func.count())
            .select_from(VerificationCode)
            .where(
                VerificationCode.target == target,
                VerificationCode.type == code_type,
                VerificationCode.purpose == purpose,
                VerificationCode.created_at >= hourly_window_start,
            )
        )
        hourly_count = int(hourly_count_row.scalar_one() or 0)
        if hourly_count >= _MAX_CODES_PER_HOUR:
            raise VerificationServiceError(
                "验证码请求过于频繁，请稍后再试",
                status_code=429,
            )

        # Invalidate any still-active code for this (target, type, purpose).
        expires_at = now + timedelta(minutes=settings.VERIFICATION_CODE_EXPIRE_MINUTES)
        await db.execute(
            update(VerificationCode)
            .where(
                VerificationCode.target == target,
                VerificationCode.type == code_type,
                VerificationCode.purpose == purpose,
                VerificationCode.used_at.is_(None),
                VerificationCode.expires_at >= now,
            )
            .values(used_at=now)
        )

        code = VerificationService.generate_code()
        record = VerificationCode(
            target=target,
            code=code,
            type=code_type,
            purpose=purpose,
            expires_at=expires_at,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def verify_code(
        db: AsyncSession,
        target: str,
        code_type: str,
        purpose: str,
        code: str,
    ) -> bool:
        """Validate a verification code with single-use semantics.

        The newest unused, unexpired code for (target, type, purpose) is
        loaded and compared in constant time. Regardless of match, the code
        is marked as consumed so an attacker cannot retry the same record.
        This caps the brute-force probability at roughly 1 / 1_000_000 per
        issued code, and the issuance rate is itself throttled in
        ``create_code``.
        """
        if code is None:
            return False
        code = str(code)

        now = datetime.utcnow()
        result = await db.execute(
            select(VerificationCode)
            .where(
                VerificationCode.target == target,
                VerificationCode.type == code_type,
                VerificationCode.purpose == purpose,
                VerificationCode.used_at.is_(None),
                VerificationCode.expires_at >= now,
            )
            .order_by(VerificationCode.created_at.desc())
            .limit(1)
        )
        record: Optional[VerificationCode] = result.scalars().first()
        if not record:
            return False

        # Consume the code unconditionally — wrong guesses must not get a retry.
        record.used_at = now
        matches = hmac.compare_digest(str(record.code), code)
        await db.commit()
        return matches
