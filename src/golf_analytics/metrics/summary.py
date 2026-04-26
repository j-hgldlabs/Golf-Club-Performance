from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass(frozen=True)
class CarrySummary:
    longest_value: float
    longest_club: str
    shortest_value: float
    shortest_club: str


def carry_summary(df: pd.DataFrame) -> CarrySummary:
    """Compute hero metrics for the avg carry dataset."""
    if "Base Carry" not in df.columns or "Club Type" not in df.columns:
        raise ValueError("Expected columns: 'Club Type' and 'Base Carry'")

    s = df["Base Carry"]
    longest_idx = s.idxmax()
    shortest_idx = s.idxmin()

    return CarrySummary(
        longest_value=float(s.loc[longest_idx]),
        longest_club=str(df.loc[longest_idx, "Club Type"]),
        shortest_value=float(s.loc[shortest_idx]),
        shortest_club=str(df.loc[shortest_idx, "Club Type"]),
    )
