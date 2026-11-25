"""app.state 보관함 이름 가드: app/ 안에서 쓰는 이름은 모두 StateName에 있어야 한다."""

import re
from pathlib import Path

import pytest
from fastapi import FastAPI

from app.api.state import KNOWN_NAMES, StateName, get_state, set_state

APP = Path(__file__).resolve().parents[1] / "app"
# application.state.X / app.state.X / request.app.state.X 와 getattr(<...>.state, "X")
ATTRIBUTE = re.compile(r"\b(?:application|app)\.state\.([A-Za-z_][A-Za-z0-9_]*)")
GETATTR = re.compile(r"getattr\(\s*[\w.]*\bstate\s*,\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']")
CONSTANT = re.compile(r"\bStateName\.([A-Z][A-Z0-9_]*)")


def used_names(*, include_constants: bool = False) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for path in APP.rglob("*.py"):
        if path.name == "state.py" and path.parent.name == "api":
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in (ATTRIBUTE, GETATTR):
            for name in pattern.findall(text):
                found.setdefault(name, set()).add(str(path.relative_to(APP)))
        if include_constants:
            for const in CONSTANT.findall(text):
                found.setdefault(getattr(StateName, const), set()).add(str(path.relative_to(APP)))
    return found


def test_app_uses_only_registered_state_names():
    unknown = {n: sorted(f) for n, f in used_names().items() if n not in KNOWN_NAMES}
    assert not unknown, f"StateName에 없는 보관함 이름: {unknown}"


def test_registered_names_are_all_used_somewhere():
    # 쓰지 않는 이름이 목록에 남지 않게 한다.
    assert KNOWN_NAMES <= set(used_names(include_constants=True))


def test_get_and_set_roundtrip_and_reject_unknown():
    application = FastAPI()
    assert get_state(application, StateName.MAIL_API) is None
    set_state(application, StateName.MAIL_API, "x")
    assert application.state.mail_api == "x"  # 테스트가 직접 꽂는 방식과 같은 보관함
    assert get_state(application, StateName.MAIL_API) == "x"
    with pytest.raises(KeyError):
        get_state(application, "mail_apii")
    with pytest.raises(KeyError):
        set_state(application, "mail_apii", 1)
