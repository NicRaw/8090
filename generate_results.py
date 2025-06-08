#!/usr/bin/env python3
"""
generate_results.py  –  Windows-friendly one-file solution
----------------------------------------------------------
• Reads private_cases.json
• Calls calculate_reimbursement.calculate_reimbursement(...)
• Writes one numeric result per line to private_results.txt
"""

import json, pathlib, sys, time

# --- 1. load private cases ---------------------------------------------------
CASES = pathlib.Path("private_cases.json")
if not CASES.exists():
    sys.exit("private_cases.json not found!")

with CASES.open("r", encoding="utf-8") as fh:
    data = json.load(fh)

# --- 2. import your reimbursement function ----------------------------------
try:
    from calculate_reimbursement import calculate_reimbursement as calc
except ImportError as e:
    sys.exit("Cannot import calculate_reimbursement(): " + str(e))

# --- 3. process & write results ---------------------------------------------
out = pathlib.Path("private_results.txt").open("w", encoding="utf-8")
start = time.time()

for i, case in enumerate(data, 1):
    if i % 100 == 0:
        print(f"{i}/{len(data)} …")

    days = case["trip_duration_days"]
    miles = case["miles_traveled"]
    recs  = case["total_receipts_amount"]

    try:
        val = calc(days, miles, recs)
        out.write(f"{val}\n")
    except Exception as ex:
        print(f"Case {i} failed:", ex)
        out.write("ERROR\n")

out.close()
print(f"\n✅  Done – wrote {i} lines to private_results.txt in {time.time()-start:0.1f}s")
