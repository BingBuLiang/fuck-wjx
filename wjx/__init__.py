"""问卷星平台包。

`main()` 仅保留为兼容入口，平台专属实现已迁移到 `wjx.provider`。
"""

from software.app.version import __VERSION__


def main():
    from software.app.main import main as _main

    return _main()


__all__ = [
    "main",
    "__VERSION__",
]


