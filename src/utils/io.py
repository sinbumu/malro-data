from pathlib import Path
from typing import Iterable

import pandas as pd


def read_csvs(paths: Iterable[Path]) -> pd.DataFrame:
    frames = [pd.read_csv(p) for p in paths]
    return pd.concat(frames, ignore_index=True)
