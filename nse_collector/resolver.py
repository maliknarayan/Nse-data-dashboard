"""Resolve a dataset's ``fn`` string to a real callable.

"module.function" is resolved against nselib's submodules. The special prefix
"custom." resolves against this package's custom_fetchers module instead.
Resolution is lazy and cached, so a submodule that fails to import (e.g.
nselib.cash_market in some builds) only breaks the datasets that use it, never
the whole collector.
"""

from __future__ import annotations

import importlib
from functools import lru_cache
from typing import Callable

_NSE_MODULES = {"capital_market", "derivatives", "indices", "cash_market", "debt"}


@lru_cache(maxsize=None)
def resolve(fn_path: str) -> Callable:
    if "." not in fn_path:
        raise ValueError(f"fn must be 'module.function', got {fn_path!r}")
    module_name, func_name = fn_path.rsplit(".", 1)

    if module_name == "custom":
        module = importlib.import_module(f"{__package__}.custom_fetchers")
    elif module_name in _NSE_MODULES:
        module = importlib.import_module(f"nselib.{module_name}")
    else:
        raise ValueError(
            f"unknown module {module_name!r}; allowed: {sorted(_NSE_MODULES)} or 'custom'"
        )

    fn = getattr(module, func_name, None)
    if not callable(fn):
        raise AttributeError(f"{fn_path} is not a callable in the resolved module")
    return fn


def validate_registry(reg: dict[str, dict]) -> dict[str, str]:
    """Try to resolve every dataset. Returns {name: error} for failures only."""
    errors: dict[str, str] = {}
    for name, ds in reg.items():
        try:
            resolve(ds["fn"])
        except Exception as exc:  # noqa: BLE001 - report, don't crash
            errors[name] = f"{type(exc).__name__}: {exc}"
    return errors
