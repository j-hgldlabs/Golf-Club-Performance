from pathlib import Path

import pandas as pd
import pytest

from golf_analytics.io.loaders import load_avg_carry_yds


def test_load_avg_carry_from_path(tmp_path: Path):
    p = tmp_path / "avg_carry_yds.csv"
    p.write_text("Club Type,Base Carry\n7i,150\n", encoding="utf-8")
    df = load_avg_carry_yds(p)
    assert list(df.columns) == ["Club Type", "Base Carry"]
    assert df.loc[0, "Club Type"] == "7i"
