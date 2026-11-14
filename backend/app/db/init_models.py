"""模型注册入口。

Alembic autogenerate 只能看到已经 import 过的模型。
每新增一个模型文件，必须在这里 import 一次，否则迁移会漏表。

TODO(M0)：无
TODO(M1)：import User / RefreshToken / Permission / AuditLog
TODO(M2)：import Building / Room / Seat / Blackout
TODO(M3)：import Reservation / ReservationSlot
TODO(M4)：import CreditLog
TODO(M5)：import Setting / Notification / Feedback
"""
