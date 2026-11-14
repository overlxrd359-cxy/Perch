"""ORM 模型。

计划中的表（按里程碑）：
- M1: users, refresh_tokens, permissions, role_permissions, audit_logs
- M2: buildings, rooms, seats, blackouts
- M3: reservation_slots, reservations
- M4: credit_logs
- M5: settings, notifications, feedback
- M7: kb_docs, kb_chunks
- M8: ai_conversations, ai_messages, ai_runs, ai_reservation_drafts

新增模型后必须在 app/db/init_models.py 里 import，否则 alembic autogenerate 看不到。
"""
