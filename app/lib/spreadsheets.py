import json

import numpy as np
import pandas as pd

SPREADSHEET_EXTS = ("csv", "xls", "xlsx", "json")
"""Tuple of supported spreadsheet extensions."""


def read_spreadsheet(path: str):
    """Import spreadsheet from filepath."""

    if isinstance(path, str):
        # assert os.path.exists(path), f"File doesn't exist at {path}."

        if path.endswith(".xlsx") or path.endswith(".xls"):
            df = pd.read_excel(path, dtype=str)
        elif path.endswith(".json"):
            # df = pd.read_json(path, dtype=str, orient="records")
            data = None
            with open(path, mode="r") as f:
                data = json.load(f)

            df = pd.json_normalize(data)
        else:
            df = pd.read_csv(path, dtype=str)
    else:
        df = pd.read_csv(path, dtype=str)

    df.replace(np.nan, "", inplace=True)

    return df
