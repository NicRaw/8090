#!/usr/bin/env python3
"""Legacy travel‑reimbursement emulator – v1.2

Adds two data‑verified tweaks that push the public‑set MAE from ~163 → ~155:

1. **Road‑warrior one‑day credit**
    • `+ $235` when the traveller does a single‑day hop > 500 miles.

2. **Low‑mileage spend cap for 3–4‑day trips**
    • If total miles ≤ 100 *and* total receipts exceed `900 $/day`, claw back
      `90 ¢` of every excess dollar.

Everything else (fortnight parity, dynamic long‑trip penalty, etc.) is retained
from v1.1.
"""
from __future__ import annotations
import sys, math, json, statistics, pathlib

# ────────────────────────────────────────────────────────────
# 1  Constants
# ────────────────────────────────────────────────────────────
C = {
    # Core pay components
    "BASE"        : 97.2,
    "LONG_K"      : 0.111,

    "M_DELTA"     : (-261, -25, 21, 254, 314),

    # Receipt curves
    "R12_LOW"     : 0.60, "R12_HIGH": 0.15, "R12_KNEE": 1_000.0,
    "R36_LOW"     : 0.45, "R36_HIGH": 0.15, "R36_KNEE": 1_000.0,
    "R7_BASE"     : 0.45, "R7_SPILL": 0.15, "R7_KNEE_PD": 150.0,
    "R7_P0"       : 0.25, "R7_P_S": 0.02,    # penalty base & slope

    # Bonuses & caps
    "FIVE_BONUS"  : 79.0, "FIVE_CAP": 1720.0,
    "WEEK_BONUS"  : 280.0,  # + week‑one (7–8 d, rpd 120‑180)
    "FORT_PEN"    : -370.0, # – week‑two (13–14 d, rpd 150‑200)

    # Efficiency parabola
    "EFF_PEAK"    : 200.0, "EFF_WIDTH": 260.0, "EFF_BONUS": 80.0,

    # New v1.2 adjustments
    "ONE_DAY_WARRIOR_BONUS": 235.0,   # + for 1‑day >500 mi
    "LMILE_CAP_PD"         : 900.0,   # $/day cap for 3‑4 d, ≤100 mi
    "LMILE_PEN_RATE"       : 0.90,    # 90 ¢ penalty per excess $

    # Historic bug multiplier
    "BUG"         : 0.60,
}

# ────────────────────────────────────────────────────────────
# 2  Helper functions
# ────────────────────────────────────────────────────────────

def long_fac(d:int)->float:                    # base dampener
    return 1.0 if d<=7 else max(0.0,1-C["LONG_K"]*math.log(d-6))


def mile_delta(d:int,m:float)->float:          # mileage tiers
    if m<=100:
        if d==1: return 0.0
        if d<=3: return -150.0
        if d<=6: return -100.0
        return -50.0
    lims=(100,300,600,1_000)
    for lim,dl in zip(lims,C["M_DELTA"]):
        if m<=lim: return dl
    return C["M_DELTA"][-1]


def rec_1_6(d,rec,low,hi,knee_pd):             # receipts helper
    knee=knee_pd*d
    return low*rec if rec<=knee else low*knee+hi*(rec-knee)


def rec_7_plus(d:int,rec:float)->float:        # long‑trip receipts
    knee=C["R7_KNEE_PD"]*d
    base=C["R7_BASE"]*min(rec,knee)
    spill=C["R7_SPILL"]*max(0, min(rec-knee, knee))
    pen_rate=C["R7_P0"]+C["R7_P_S"]*d
    penalty=pen_rate*max(0,rec-2*knee)
    return base+spill-penalty


def rec_comp(d:int,rec:float)->float:
    if d<=2: return rec_1_6(d,rec,C["R12_LOW"],C["R12_HIGH"],C["R12_KNEE"])
    if d<=6: return rec_1_6(d,rec,C["R36_LOW"],C["R36_HIGH"],C["R36_KNEE"])
    return rec_7_plus(d,rec)


def eff_bonus(d:int,m:float)->float:           # efficiency parabola
    mpd=m/d; sc=1-((mpd-C["EFF_PEAK"])/C["EFF_WIDTH"])**2
    peak=80 if d<=6 else C["EFF_BONUS"]
    val=sc*peak
    return val if d>=7 else max(0,val)


def fortnight_adj(d:int,rpd:float)->float:     # week‑parity rule
    if 7<=d<=8 and 120<=rpd<=180: return C["WEEK_BONUS"]
    if 13<=d<=14 and 150<=rpd<=200: return C["FORT_PEN"]
    return 0.0


def low_mile_penalty(d:int,m:float,rec:float)->float:
    """Claw back overspend on 3–4 day trips that barely drive."""
    if d in (3,4) and m<=100:
        cap=C["LMILE_CAP_PD"]*d
        excess=max(0.0, rec-cap)
        return -C["LMILE_PEN_RATE"]*excess
    return 0.0


def hits_bug(r:float)->bool: return int(round(r*100))%100 in (49,99)

# ────────────────────────────────────────────────────────────
# 3  Main calculation
# ────────────────────────────────────────────────────────────

def calculate_reimbursement(d:int,m:float,r:float)->float:
    total=(C["BASE"]*d*long_fac(d)+mile_delta(d,m)+rec_comp(d,r)+eff_bonus(d,m))

    # 5‑day bonus + cap
    if d==5:
        total=min(total+C["FIVE_BONUS"],C["FIVE_CAP"])

    # v1.2 one‑day road‑warrior credit
    if d==1 and m>500:
        total+=C["ONE_DAY_WARRIOR_BONUS"]

    # v1.2 low‑mileage spend penalty (3‑4 d, ≤100 mi)
    total+=low_mile_penalty(d,m,r)

    # fortnight parity
    total+=fortnight_adj(d,r/d)

    # historic .49/.99 bug
    if hits_bug(r):
        total*=C["BUG"]

    return round(total,2)

# ────────────────────────────────────────────────────────────
# 4  CLI entry
# ────────────────────────────────────────────────────────────
if __name__=="__main__":
    if len(sys.argv)==4:
        print(f"{calculate_reimbursement(int(sys.argv[1]),float(sys.argv[2]),float(sys.argv[3])):.2f}")
    elif len(sys.argv)==3 and sys.argv[1]=="--tune":
        rows=json.loads(pathlib.Path(sys.argv[2]).read_text())[1:]
        errs=[abs(calculate_reimbursement(r["input"]["trip_duration_days"],
                                         r["input"]["miles_traveled"],
                                         r["input"]["total_receipts_amount"]) - r["expected_output"]) for r in rows]
        print(f"MAE {statistics.mean(errs):.2f}  Max {max(errs):.2f}")
    else:
        print("Usage: calc_reimbursement.py <days> <miles> <receipts>  |  --tune public_cases.json")
