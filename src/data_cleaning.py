# src/data_cleaning.py
import pandas as pd
import numpy as np


def load_raw(path: str) -> pd.DataFrame:
    """Load the raw CSV and parse the date column."""
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y")
    return df

def add_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Flag cancelled tickets (qty=0) and gift/sample rows (amount=0, qty>0).
    Rows are kept, not dropped, for traceability."""
    df = df.copy()
    df["is_cancelled"] = df["sell_in_quantity"] == 0
    df["is_gift"] = (df["sell_in_amount"] == 0) & (df["sell_in_quantity"] > 0)
    return df

def fill_missing_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Fill missing category/subcategory/brand/basket by mapping from other
    rows with the same product_code (these fields are constant per SKU)."""
    df = df.copy()
    meta_cols = ["product_name", "category", "subcategory", "brand", "basket"]

    lookup = (
        df.dropna(subset=meta_cols)
        .drop_duplicates("product_code")
        .set_index("product_code")[meta_cols]
    )

    for col in meta_cols:
        missing_mask = df[col].isnull()
        if missing_mask.any():
            df.loc[missing_mask, col] = df.loc[missing_mask, "product_code"].map(lookup[col])

    return df

def fill_discount_bruto(df: pd.DataFrame) -> pd.DataFrame:
    """Impute discount/bruto using their algebraic relation with sell_in_amount:
    bruto = amount / (1 - discount). Organic sales (no id_combo) default to
    discount=0 when still missing."""
    df = df.copy()

    # bruto = amount / (1 - discount)  =>  discount = 1 - (amount / bruto)
    can_derive_bruto = df["bruto"].isnull() & df["discount"].notnull() & (df["discount"] < 1)
    df.loc[can_derive_bruto, "bruto"] = df.loc[can_derive_bruto, "sell_in_amount"] / (
        1 - df.loc[can_derive_bruto, "discount"]
    )

    can_derive_discount = df["discount"].isnull() & df["bruto"].notnull() & (df["bruto"] > 0)
    df.loc[can_derive_discount, "discount"] = 1 - (
        df.loc[can_derive_discount, "sell_in_amount"] / df.loc[can_derive_discount, "bruto"]
    )

    # rows with no promo (id_combo null) and still missing either column:
    # treat as an organic sale, discount=0
    no_promo = df["id_combo"].isnull()
    df.loc[df["discount"].isnull() & no_promo, "discount"] = 0.0
    df.loc[df["bruto"].isnull() & no_promo, "bruto"] = df.loc[
        df["bruto"].isnull() & no_promo, "sell_in_amount"
    ]

    return df

def fill_residual_discount_bruto(df: pd.DataFrame) -> pd.DataFrame:
    """Handle rows that belong to a promotion but have both discount and
    bruto missing (no algebraic derivation possible): impute discount with
    the average discount of that same id_combo, then derive bruto from it."""
    df = df.copy()

    # combo-level average discount, from rows that do have a value
    combo_avg_discount = df.groupby("id_combo")["discount"].mean()

    still_missing_discount = df["discount"].isnull()
    df.loc[still_missing_discount, "discount"] = df.loc[
        still_missing_discount, "id_combo"
    ].map(combo_avg_discount)

    # derive bruto where possible (skips division by zero when discount == 1)
    can_derive_bruto = df["bruto"].isnull() & df["discount"].notnull() & (df["discount"] < 1)
    df.loc[can_derive_bruto, "bruto"] = df.loc[can_derive_bruto, "sell_in_amount"] / (
        1 - df.loc[can_derive_bruto, "discount"]
    )

    return df