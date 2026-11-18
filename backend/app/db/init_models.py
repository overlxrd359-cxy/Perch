"""模型注册入口。

Alembic autogenerate 只能看到已经 import 过的模型。
每新增一个模型文件，必须在这里 import 一次，否则迁移会漏表。
"""

from __future__ import annotations

from app.models.user import User

# M1 后续：RefreshToken / Permission / AuditLog
# M2：Building / Room / Seat / Blackout
# M3：Reservation / ReservationSlot
# M4：CreditLog
# M5：Setting / Notification / Feedback

__all__ = ["User"]
