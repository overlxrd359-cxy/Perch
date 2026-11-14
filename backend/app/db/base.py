"""ORM 基类与公共 Mixin。

TODO(M0)：
- [ ] Base(DeclarativeBase)
- [ ] TimestampMixin：created_at / updated_at
- [ ] IntPKMixin：id BIGINT 自增
- [ ] utcnow() 工具函数

约定：时间统一存 UTC 的 DATETIME（不带时区），展示层再转本地。
"""
