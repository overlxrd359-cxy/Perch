"""占位冒烟测试。

目的：保证 CI 中的 pytest 链路可用，M1 起替换为真实测试。
"""

from __future__ import annotations


def test_test_infrastructure_works() -> None:
    assert True
