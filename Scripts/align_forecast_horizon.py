"""
Align all forecast outputs to a single 6-month horizon.

Fixes "ValueError: All arrays must be of the same length" caused by some
files still being in the old 3-month format while others produce 6 months.
Short arrays are padded with NaN so pd.DataFrame() never fails.
"""
import sys
import pandas as pd
import os

# Avoid UnicodeEncodeError on Windows consoles when printing ₱ / ñ chars
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ==========================
# 1. CONFIGURATION
# ==========================
FORECAST_HORIZON = 6                                     # new target period
MONTH_COLS = [f"Month {i}" for i in range(1, FORECAST_HORIZON + 1)]

BASE = os.path.join(os.path.dirname(__file__), "..")

# Each entry: (file path relative to BASE, kind)
#   kind="wide"   -> many-row table keyed by Month 1..N  (municipal table)
#   kind="series" -> single flat array of forecast values (one per month)
FILES = [
    ("data/Dashboard_Ready/fancy_forecast.xlsx",   "series"),
    ("data/Dashboard_Ready/variety_forecast.xlsx", "series"),
    ("data/Dashboard_Ready/yield_forecast.xlsx",   "series"),
    ("data/data/Municipal_Price_Forecast_Results.xlsx", "wide"),
]


# ==========================
# 2. READ + AUDIT LENGTHS
# ==========================
def load_series(path):
    """Read a flat single-column value array, dropping NaNs."""
    raw = pd.read_excel(path, header=None).iloc[:, 0].dropna().tolist()
    return raw


def load_wide(path):
    """Read a table that already uses 'Month N' columns."""
    return pd.read_excel(path)


def audit(name, length, expected):
    """Print a warning when an array is shorter than the target horizon."""
    status = "OK" if length == expected else (f"SHORT by {expected - length}" if length < expected else f"LONG by {length - expected}")
    print(f"[{status:<12}] {name:<45} length={length:<4} expected={expected}")
    return length


# ==========================
# 3. PAD ANY SHORT ARRAY TO 6 MONTHS
# ==========================
def pad_values(values, horizon=FORECAST_HORIZON, fill=float("nan")):
    """Pad or truncate a list so its length exactly equals the horizon."""
    return list(values[:horizon]) + [fill] * max(0, horizon - len(values))


# ==========================
# 4. STANDARDIZE EVERYTHING
# ==========================
def main():
    print("=" * 78)
    print("FORECAST HORIZON ALIGNMENT : {} months".format(FORECAST_HORIZON))
    print("=" * 78)

    series_rows = []   # one row per flat-array file, months as columns
    wide_tables = []   # many-row tables, padded with Month 4-6 = NaN

    for rel_path, kind in FILES:
        path = os.path.normpath(os.path.join(BASE, rel_path))
        print(f"\n-> {rel_path}")

        if kind == "series":
            values = load_series(path)
            audit(rel_path, len(values), FORECAST_HORIZON)

            # Align each value array to the 6-month axis.
            # If the file already gave 6 values, they map exactly onto
            # Month 1..6; if old 3 values, they fill Months 1..3 and the
            # remaining months become NaN.
            padded = pad_values(values)
            row = dict(zip(MONTH_COLS, padded))
            row["Source"] = os.path.basename(rel_path)
            series_rows.append(row)

        else:  # wide
            df = load_wide(path)
            missing = [c for c in MONTH_COLS if c not in df.columns]
            for c in missing:
                df[c] = float("nan")           # pad missing months (Month 4-6)
            df = df[MONTH_COLS + [c for c in df.columns if c not in MONTH_COLS]]
            wide_tables.append(df)
            audit(rel_path, len(missing) + 3, FORECAST_HORIZON)
            print(f"   columns   : {list(df.columns)}")

    # ==========================
    # 5. BUILD THE CLEAN DATAFRAME (NO LENGTH MISMATCH ANYMORE)
    # ==========================
    series_df = pd.DataFrame(series_rows)[["Source"] + MONTH_COLS]

    clean = series_df
    if wide_tables:
        clean = pd.concat([clean, pd.concat(wide_tables, ignore_index=True)],
                          ignore_index=True, sort=False)

    print("\n" + "=" * 78)
    print(f"SHAPE    : {clean.shape}")
    print(f"COLUMNS  : {list(clean.columns)}")
    print("NaN count per aligned month column:")
    for c in MONTH_COLS:
        print(f"   {c:<8}: {int(clean[c].isna().sum())} NaN")
    print("=" * 78)

    return clean


if __name__ == "__main__":
    result = main()
    print("\nFirst aligned rows:\n", result.head(8).to_string(index=False))