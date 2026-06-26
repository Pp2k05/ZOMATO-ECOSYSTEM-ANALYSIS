import re

log_path = r"C:\Users\parth\.gemini\antigravity\brain\06025eac-b85c-4704-92ea-a1afd27b6c92\.system_generated\tasks\task-134.log"

with open(log_path, encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

kw_gained = {}
prev_rows  = 0

for line in lines:
    m = re.search(r"'(.+?)' \| rows: ([\d,]+)", line)
    if m:
        kw   = m.group(1)
        rows = int(m.group(2).replace(",", ""))
        gained = rows - prev_rows
        if gained > 0:
            kw_gained[kw] = kw_gained.get(kw, 0) + gained
        prev_rows = rows

brand = {"Zomato": 0, "Blinkit": 0, "HyperPure": 0, "District": 0}
for kw, cnt in kw_gained.items():
    kl = kw.lower()
    if "blinkit" in kl or "grofers" in kl:
        brand["Blinkit"] += cnt
    elif "hyper" in kl:
        brand["HyperPure"] += cnt
    elif "district" in kl:
        brand["District"] += cnt
    else:
        brand["Zomato"] += cnt

total = sum(brand.values())
print(f"Reddit rows so far: {prev_rows:,}  |  Attributed: {total:,}")
print()
for b, c in brand.items():
    pct = (c / total * 100) if total else 0
    bar = "#" * int(pct / 2)
    print(f"  {b:<12} {c:>5,} rows  ({pct:.0f}%)  {bar}")
