#!/usr/bin/env python
"""Identity checks over content/facts_*.json.

Checks, per company-year (see docs/CONTENT_FORMAT.md):
  1. total_assets == total_liabilities + total_equity  (within 0.5% of assets)
  2. cfo + cfi + cff + fx_effect == net_change_cash    (within 1% of |change|, min 1.0)
  3. gross_profit == revenue - cost_of_revenue          (within 0.5, when all present)

Missing fx_effect is treated as 0. Exits nonzero on any failure.
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    files = sorted(glob.glob(os.path.join(ROOT, "content", "facts_*.json")))
    if not files:
        print("no content/facts_*.json files found")
        return 1

    data = {}  # (company, fy) -> {item: value}
    for path in files:
        for row in json.load(open(path)):
            data.setdefault((row["company_id"], row["fiscal_year"]), {})[row["item"]] = row["value"]

    failures = 0
    checked = 0
    for (cid, fy), items in sorted(data.items()):
        # 1. balance sheet identity
        a, l, e = items.get("total_assets"), items.get("total_liabilities"), items.get("total_equity")
        if a is not None and e is not None:
            if l is None:
                l = a - e  # derive for sparse filers (banks)
            gap = abs(a - (l + e))
            checked += 1
            if gap > 0.005 * abs(a):
                print(f"FAIL {cid} FY{fy}: assets {a} != liabilities {l} + equity {e} (gap {gap:.1f})")
                failures += 1
        # 2. cash flow identity
        cfo, cfi, cff = items.get("cfo"), items.get("cfi"), items.get("cff")
        fx = items.get("fx_effect", 0.0)
        chg = items.get("net_change_cash")
        if None not in (cfo, cfi, cff, chg):
            gap = abs((cfo + cfi + cff + fx) - chg)
            tol = max(1.0, 0.01 * abs(chg))
            checked += 1
            if gap > tol:
                print(f"FAIL {cid} FY{fy}: cfo+cfi+cff+fx = {cfo + cfi + cff + fx:.1f} != net_change_cash {chg} (gap {gap:.1f})")
                failures += 1
        # 3. gross profit consistency
        rev, cor, gp = items.get("revenue"), items.get("cost_of_revenue"), items.get("gross_profit")
        if None not in (rev, cor, gp):
            gap = abs(gp - (rev - cor))
            checked += 1
            if gap > 0.5:
                print(f"FAIL {cid} FY{fy}: gross_profit {gp} != revenue {rev} - cost_of_revenue {cor} (gap {gap:.1f})")
                failures += 1

    print(f"{checked} identity checks over {len(data)} company-years in {len(files)} file(s): "
          f"{'ALL PASS' if failures == 0 else f'{failures} FAILURES'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
