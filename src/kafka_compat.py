"""
kafka-python 2.0.2 wheels ship a vendored ``six`` layout that breaks on Python 3.12
(``ModuleNotFoundError: kafka.vendor.six.moves``). Import this module **before** any
``from kafka import ...`` so the stdlib ``six`` moves namespace is wired in.

On Python 3.11 and below this is a no-op. Your laptop can stay on 2.0.2 + 3.11 unchanged.
"""

from __future__ import annotations

import sys

if sys.version_info >= (3, 12):
    import six

    sys.modules.setdefault("kafka.vendor.six.moves", six.moves)
