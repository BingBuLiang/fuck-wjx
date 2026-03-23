"""WJX 包精简入口。"""

from software.app.version import __VERSION__


def main():
    from software.app.main import main as _main

    return _main()


__all__ = [
    "main",
    "__VERSION__",
]


