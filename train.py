#!/usr/bin/env python3
"""
train_test_random_forest.py

Train a Random-Forest regressor on half of the public reimbursement data
and evaluate on the held-out half.

Requirements
------------
pip install pandas numpy scikit-learn matplotlib joblib
"""

import json
import pathlib
import random
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

# ----------------------- config ---------------------------
DATA_FILE   = "public_cases.json"
MODEL_FILE  = "rf_reimbursement.pkl"
TEST_SIZE   = 0.50          # 50 / 50 split
RANDOM_SEED = 32            # reproducible split & RF
RF_PARAMS   = dict(
    n_estimators = 400,
    max_depth    = None,
    min_samples_split = 4,
    random_state = RANDOM_SEED,
)
# ----------------------------------------------------------

def load_flat_json(path: str | pathlib.Path) -> pd.DataFrame:
    """Load the public JSON and flatten input → columns."""
    with open(path, "r", encoding="utf-8") as fh:
        rows = json.load(fh)[1:]      # skip header row 0
    df = pd.json_normalize(rows)
    # Rename for convenience
    df = df.rename(columns={
        "input.trip_duration_days": "trip_days",
        "input.miles_traveled": "miles",
        "input.total_receipts_amount": "receipts",
        "expected_output": "expected",
    })[["trip_days", "miles", "receipts", "expected"]]
    return df

def train_test_split_df(df: pd.DataFrame, test_size=0.5, seed=42):
    idx = list(df.index)
    random.Random(seed).shuffle(idx)
    cut = int(len(idx) * (1 - test_size))
    train_idx, test_idx = idx[:cut], idx[cut:]
    return df.loc[train_idx].reset_index(drop=True), df.loc[test_idx].reset_index(drop=True)

def main() -> None:
    df = load_flat_json(DATA_FILE)
    train_df, test_df = train_test_split_df(df, TEST_SIZE, RANDOM_SEED)

    X_train = train_df[["trip_days", "miles", "receipts"]].values
    y_train = train_df["expected"].values
    X_test  = test_df[["trip_days", "miles", "receipts"]].values
    y_test  = test_df["expected"].values

    rf = RandomForestRegressor(**RF_PARAMS)
    rf.fit(X_train, y_train)

    y_pred = rf.predict(X_test)
    mae    = mean_absolute_error(y_test, y_pred)
    worst5 = pd.Series(np.abs(y_pred - y_test)).nlargest(5).tolist()

    print(f"Train rows : {len(train_df)}")
    print(f"Test  rows : {len(test_df)}")
    print(f"MAE (test) : ${mae:,.2f}")
    print("Worst-5    :", [f"${w:,.2f}" for w in worst5])

    # Save model
    joblib.dump(rf, MODEL_FILE)
    print(f"Model saved → {MODEL_FILE}")

    # Optional quick scatter (requires matplotlib)
    try:
        import matplotlib.pyplot as plt
        plt.figure(figsize=(6,4))
        plt.scatter(y_test, y_pred, alpha=0.6, s=18)
        plt.plot([y_test.min(), y_test.max()],
                 [y_test.min(), y_test.max()], "--", color="black")
        plt.xlabel("Actual"); plt.ylabel("Predicted")
        plt.title(f"Random Forest – MAE ${mae:,.2f}")
        plt.tight_layout()
        plt.show()
    except ImportError:
        pass      # matplotlib not installed – skip plot

if __name__ == "__main__":
    main()
