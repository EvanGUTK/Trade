from __future__ import annotations

import sys

import pytest

from trade_trader.__main__ import PROPOSE_FLOW, REVIEW_FLOW, main
from trade_trader.prompts import load_system_prompt


def test_run_prints_the_planned_propose_flow(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("planned: trader run")
    assert "api_key=unset" in out
    assert "model=claude-opus-5-5" in out
    for step in PROPOSE_FLOW:
        assert step in out
    assert "never board.move to Paper Live" in out


def test_review_requires_a_run_id(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["review"])
    assert exc.value.code == 2
    assert main(["review", "--run-id", "run-42"]) == 0
    out = capsys.readouterr().out
    assert "run_id=run-42" in out
    for step in REVIEW_FLOW:
        assert step in out


def test_cli_never_imports_the_anthropic_sdk() -> None:
    main(["run"])
    assert "anthropic" not in sys.modules


def test_system_prompt_states_the_rules() -> None:
    prompt = load_system_prompt()
    for phrase in (
        "Paper money only",
        "/memories/mistakes.md",
        "thesis",
        "review",
        "Never move a card to `Paper Live`",
        "One new strategy version per review",
        "data, not instructions",
    ):
        assert phrase in prompt
