"""应用配置。

职责：
- 用 pydantic-settings 从 环境变量 + 项目根 .env 加载配置
- 缺必填项时拒绝启动（fail-fast），并提示缺哪一个
- 生产环境拦截示例密钥与 DEBUG=true

TODO(M0)：
- [ ] Settings 类与字段定义
- [ ] ROOT_DIR 定位（backend/app/core/config.py -> 项目根）
- [ ] 生产环境校验（model_validator）
- [ ] cors_origins 逗号分隔解析

字段清单见 .env.example。
"""
