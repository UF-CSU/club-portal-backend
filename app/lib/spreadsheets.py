import json

import numpy as np
import pandas as pd
from django.core.files import File

SPREADSHEET_EXTS = ("csv", "xls", "xlsx", "json")
"""Tuple of supported spreadsheet extensions."""


def read_spreadsheet(file: File):
    """Import spreadsheet from filepath."""

    path = file.name

    if file.name.endswith(".xlsx") or path.endswith(".xls"):
        df = pd.read_excel(file.open(mode="r"), dtype=str)
    elif file.name.endswith(".json"):
        data = json.load(file.open(mode="r"))
        df = pd.json_normalize(data)
    else:
        df = pd.read_csv(file.open(mode="r"), dtype=str)

    df.replace(np.nan, "", inplace=True)

    return df
