"""The command-line entry point: input formats and exit codes."""

from __future__ import annotations

import json

import pandas as pd
import pytest
from scan import main


def _run(capsys, *argv: str) -> dict:
    assert main([*argv, "--format", "json"]) == 0
    return json.loads(capsys.readouterr().out)


def test_tsv_reads_the_same_as_csv(tmp_path, examples_dir, capsys) -> None:
    csv_path = examples_dir / "reported_stats.csv"
    tsv_path = tmp_path / "reported_stats.tsv"
    pd.read_csv(csv_path).to_csv(tsv_path, sep="\t", index=False)
    from_csv = _run(capsys, "--reported-stats", str(csv_path))
    from_tsv = _run(capsys, "--reported-stats", str(tsv_path))
    assert from_tsv["summary"] == from_csv["summary"]


def test_xlsx_reads_the_same_as_csv(tmp_path, examples_dir, capsys) -> None:
    pytest.importorskip("openpyxl")
    csv_path = examples_dir / "reported_stats.csv"
    xlsx_path = tmp_path / "reported_stats.xlsx"
    pd.read_csv(csv_path).to_excel(xlsx_path, index=False)
    from_csv = _run(capsys, "--reported-stats", str(csv_path))
    from_xlsx = _run(capsys, "--reported-stats", str(xlsx_path))
    assert from_xlsx["summary"] == from_csv["summary"]


def test_a_missing_file_is_an_error(capsys) -> None:
    assert main(["no_such_file.csv"]) == 2
    assert "no such file" in capsys.readouterr().err


def test_an_unknown_group_is_an_error(examples_dir, capsys) -> None:
    assert main([str(examples_dir / "clean_trial.csv"), "--checks", "nonsense"]) == 2
    assert "Unknown check groups" in capsys.readouterr().err
