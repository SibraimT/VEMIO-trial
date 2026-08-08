# src/data_cleaning.py
import pandas as pd
import numpy as np


def load_raw(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y")
    return df

def add_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["is_cancelled"] = df["sell_in_quantity"] == 0
    df["is_gift"] = (df["sell_in_amount"] == 0) & (df["sell_in_quantity"] > 0)
    return df