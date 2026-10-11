from __future__ import annotations

import pytest

from trade_strategies.__main__ import build_parser, main


def test_help_lists_planned_flags(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for flag in (
        "--strategy",
        "--session",
        "--symbols",
        "--tf",
        "--gateway",
        "--seed",
        "--bar-budget-ms",
    ):
        assert flag in out


def test_main_is_a_planned_stub(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--session", "s1", "--tf", "1d"]) == 2
    out = capsys.readouterr().out
    assert out.startswith("planned:")
    assert "session=s1" in out
