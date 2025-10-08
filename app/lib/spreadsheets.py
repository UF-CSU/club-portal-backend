import json

import numpy as np
import pandas as pd
from django.core.files import File

SPREADSHEET_EXTS = ("csv", "xls", "xlsx", "json")
"""Tuple of supported spreadsheet extensions."""


def read_spreadsheet(path: str, file: File = None):
    """Import spreadsheet from filepath."""

    if isinstance(path, str):
        # assert os.path.exists(path), f"File doesn't exist at {path}."
        # func = pd.read_csv

        if path.endswith(".xlsx") or path.endswith(".xls"):
            if file:
                df = pd.read_excel(file.open("r"), dtype=str)
            else:
                df = pd.read_excel(path, dtype=str)
        elif path.endswith(".json"):
            # df = pd.read_json(path, dtype=str, orient="records")
            if file:
                data = None
                with file.open(mode="r") as f:
                    data = json.load(f)

                df = pd.json_normalize(data)
            else:
                data = None
                with open(path) as f:
                    data = json.load(f)

                df = pd.json_normalize(data)
        else:
            if file:
                df = pd.read_csv(file.open("r"), dtype=str)
            else:
                df = pd.read_csv(path, dtype=str)
    else:
        df = pd.read_csv(path, dtype=str)

    df.replace(np.nan, "", inplace=True)

    return df
