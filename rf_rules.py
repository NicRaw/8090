#!/usr/bin/env python3
"""
rf_rule_extractor.py

Extract human-readable rules from a saved RandomForestRegressor trained on
the reimbursement public data.

Required libs
-------------
pip install pandas numpy scikit-learn joblib
# optional for RuleFit extras:
pip install sklearn-rulefit
"""

import json
import joblib
import pathlib
import numpy as np
import pandas as pd
from collections import defaultdict
from sklearn.tree import export_text

# --------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------
DATA_JSON   = "public_cases.json"         # public set (1 000 rows)
MODEL_PKL   = "rf_reimbursement.pkl"      # saved RandomForestRegressor
SEED        = 42                          # just for any randomness

# --------------------------------------------------------------------------
# 1. Load data & model
# --------------------------------------------------------------------------
def load_flat_json(path: str | pathlib.Path) -> pd.DataFrame:
    with open(path, "r", encoding="utf-8") as fh:
        rows = json.load(fh)[1:]          # skip header row
    df = pd.json_normalize(rows)
    return df.rename(columns={
        "input.trip_duration_days": "trip_days",
        "input.miles_traveled":    "miles",
        "input.total_receipts_amount": "receipts",
        "expected_output":         "expected",
    })[["trip_days", "miles", "receipts", "expected"]]

print("Loading model and data ...")
rf  = joblib.load(MODEL_PKL)
df  = load_flat_json(DATA_JSON)
X   = df[["trip_days", "miles", "receipts"]]
y   = df["expected"]

# --------------------------------------------------------------------------
# 2. Feature importances
# --------------------------------------------------------------------------
print("\n=== Feature Importances ===")
for name, val in zip(X.columns, rf.feature_importances_):
    print(f"{name:<10}: {val:0.3f}")

# --------------------------------------------------------------------------
# 3. Show best (shallow) tree for quick insight
# --------------------------------------------------------------------------
best_idx, best_r2 = max(
    enumerate(rf.estimators_),
    key=lambda t: t[1].score(X, y)
)
best_tree = rf.estimators_[best_idx]
print("\n=== Shallow text dump of best tree (depth ≤ 4) ===")
print(export_text(best_tree, feature_names=list(X.columns), max_depth=4))

# --------------------------------------------------------------------------
# 4. Aggregate high-support leaves across the forest
# --------------------------------------------------------------------------
MIN_SUPPORT = int(0.01 * len(df))   # ≥1% of rows  (==10 for 1,000 rows)
rules = []

for tree in rf.estimators_:
    leaf_ids = tree.apply(X)
    group = defaultdict(list)
    for row_idx, leaf_id in enumerate(leaf_ids):
        group[leaf_id].append(row_idx)

    for leaf_id, rows_idx in group.items():
        if len(rows_idx) < MIN_SUPPORT:
            continue   # ignore tiny leaves

        row_sample = df.iloc[rows_idx]
        median_pred = np.median(y.iloc[rows_idx])

        # path to leaf
        path_nodes = tree.decision_path(X.iloc[[rows_idx[0]]]).indices
        terms = []
        for node_id in path_nodes:
            if tree.tree_.feature[node_id] == -2:   # leaf
                continue
            fname  = X.columns[tree.tree_.feature[node_id]]
            thresh = tree.tree_.threshold[node_id]
            # direction for this sample
            go_left = X.iloc[rows_idx[0], tree.tree_.feature[node_id]] <= thresh
            sign = "<=" if go_left else ">"
            terms.append(f"{fname} {sign} {thresh:.1f}")

        rule_txt = " and ".join(terms)
        rules.append((len(rows_idx), median_pred, rule_txt))

# sort by support
rules.sort(reverse=True)

print(f"\n=== Forest rules covering ≥ {MIN_SUPPORT} rows ===")
for n, pred, cond in rules[:20]:
    print(f"[{n:3d} rows] if {cond}  ⇒  reimburse ≈ ${pred:,.2f}")

# --------------------------------------------------------------------------
# 5. (Optional) RuleFit for compact rule list
# --------------------------------------------------------------------------
try:
    from rulefit import RuleFit
    print("\nTraining RuleFit model ...")
    rf_rule = RuleFit(tree_size=4, rfsize=300, sample_fract='default',
                      max_rules=50, random_state=SEED)
    rf_rule.fit(X.values, y.values, feature_names=list(X.columns))

    rules_df = rf_rule.get_rules()
    rules_df = rules_df[rules_df.coef != 0].sort_values("importance", ascending=False)

    print("\n=== Top RuleFit rules ===")
    print(rules_df.head(15)[["rule", "support", "coef", "importance"]])
except ImportError:
    print("\n[rulefit] not installed → skipping RuleFit rule extraction")
