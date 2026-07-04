import pandas as pd  # data handling library for tables / dataframes
import numpy as np  # numerical operations (math, arrays, transformations)
from statsmodels.tsa.stattools import adfuller  # Augmented Dickey-Fuller test for stationarity

# -----------------------------
# OUTLIER HANDLING PER YEAR
# -----------------------------
def handle_outliers_per_year(df, target_cols):
    print("\n=== OUTLIER HANDLING (CAPPING PER YEAR) ===")

    for target in target_cols:
        if target in df.columns:

            print(f"\nHandling: {target}")

            def cap_series(s):
                s_clean = s.dropna()  # remove missing values for stable statistics

                # skip computation if dataset is too small
                if len(s_clean) < 10:
                    return s, pd.Series([False] * len(s), index=s.index)

                mean = s_clean.mean()  # compute mean of series
                std = s_clean.std()  # compute standard deviation

                upper = mean + 3 * std  # upper bound for outlier detection
                lower = mean - 3 * std  # lower bound for outlier detection

                # identify outliers beyond thresholds
                outlier_flag = (s > upper) | (s < lower)

                # cap extreme values to upper/lower bounds
                s_capped = np.where(s > upper, upper,
                             np.where(s < lower, lower, s))

                return pd.Series(s_capped, index=s.index), outlier_flag

            capped_values = []  # store capped series per year
            flags = []  # store outlier flags per year

            # apply outlier handling separately per year (temporal grouping)
            for year, group in df.groupby("year"):
                capped, flag = cap_series(group[target])
                capped_values.append(capped)
                flags.append(flag)

                print(f"{year}: {flag.sum()} capped values")  # log number of outliers per year

            df[target] = pd.concat(capped_values).sort_index()  # recombine capped values in correct order
            df[f"{target}_was_outlier"] = pd.concat(flags).astype(int).sort_index()  # binary flag column

    return df

# -----------------------------
# STATIONARITY TRANSFORMATION
# -----------------------------
def make_stationary(df, target_cols):
    print("\n=== APPLYING STATIONARITY TRANSFORMATIONS ===")

    for target in target_cols:
        if target in df.columns:

            # log transformation to stabilize variance and reduce skewness
            df[f"{target}_log"] = np.log1p(df[target])

            # first differencing to remove trend and make series stationary
            df[f"{target}_log_diff"] = df[f"{target}_log"].diff()

            print(f"{target}: log + differencing applied")

    return df

# -----------------------------
# STATIONARITY TEST (ADF)
# -----------------------------
def stationarity_test(df, target_cols, transformed=False):

    if transformed:
        print("\n=== STATIONARITY TEST (AFTER TRANSFORMATION) ===")
    else:
        print("\n=== STATIONARITY TEST (BEFORE TRANSFORMATION) ===")

    for target in target_cols:

        col = f"{target}_log_diff" if transformed else target

        if col not in df.columns:
            continue

        s = df[col].dropna()

        if len(s) > 10:
            result = adfuller(s)

            print(f"\n{target}")
            print("ADF:", result[0])
            print("p-value:", result[1])

            if result[1] < 0.05:
                print("Result: Stationary (Reject H₀)")
            else:
                print("Result: Non-stationary (Fail to Reject H₀)")

# -----------------------------
# MAIN EDA FUNCTION
# -----------------------------
def run_eda_municipality(file_path2):
    print("\n=== START OF ML-READY EDA (MUNICIPALITY) ===")

    # load Excel file with multiple sheets into dictionary of DataFrames
    sheets = pd.read_excel(file_path2, sheet_name=None)

    # assign sheet to a specific dataframe
    perMunicipality_df = sheets[list(sheets.keys())[0]]

    # convert year column to numeric for consistency
    for df in [perMunicipality_df]:
        if "year" in df.columns:
            df["year"] = pd.to_numeric(df["year"], errors="coerce")

    # sort data chronologically for correct time-series ordering
    if "month_num" in perMunicipality_df.columns:
        perMunicipality_df = perMunicipality_df.sort_values(["year", "month_num"])

    # -----------------------------
    # DATA OVERVIEW
    # -----------------------------
    print("\n=== DATA SHAPES ===")
    print("Municipality:", perMunicipality_df.shape)  # dataset size (rows, columns)

    # -----------------------------
    # MISSING VALUES
    # -----------------------------
    print("\n=== MISSING VALUES (%) ===")

    for name, df in {
        "Municipality": perMunicipality_df
    }.items():
        print(f"\n[{name}]")
        print((df.isnull().mean() * 100).sort_values(ascending=False).head(10))  # top missing columns

    # -----------------------------
    # TIME COVERAGE
    # -----------------------------
    print("\n=== TIME COVERAGE ===")

    for name, df in {
        "Municipality": perMunicipality_df
    }.items():

        if "year" in df.columns:
            print(f"\n{name}")
            print("Min Year:", df["year"].min())  # earliest year in dataset
            print("Max Year:", df["year"].max())  # latest year in dataset
            print("Unique Years:", df["year"].nunique())  # number of unique years

    # -----------------------------
    # TARGET VARIABLES
    # -----------------------------
    target_cols = [
        "hybridpremium_dry",
        "hybridpremium_wet",
        "hybridordinary_dry",
        "hybridordinary_wet",
        "inbredpremium_dry",
        "inbredpremium_wet",
        "inbredordinary_dry",
        "inbredordinary_wet"
    ]

    # apply outlier handling per year for selected targets
    perMunicipality_df = handle_outliers_per_year(perMunicipality_df, target_cols)

    # STATIONARITY TEST (BEFORE)
    stationarity_test(perMunicipality_df, target_cols)

    # apply stationarity transformation (log + differencing)
    perMunicipality_df = make_stationary(perMunicipality_df, target_cols)

    # -----------------------------
    # STATIONARITY TEST (AFTER)
    # -----------------------------
    stationarity_test(
        perMunicipality_df,
        target_cols,
        transformed=True
    )

    # -----------------------------
    # TARGET STATISTICS
    # -----------------------------
    print("\n=== TARGET ANALYSIS (PER YEAR) ===")

    for target in target_cols:
        if target in perMunicipality_df.columns:
            print(f"\n--- {target} ---")
            print(
                perMunicipality_df.groupby("year")[target]
                .agg(["mean", "std", "min", "max"])  # summary statistics per year
                .tail(10)
            )

    # -----------------------------
    # FINAL CONCLUSION
    # -----------------------------
    print("\n=== FINAL CONCLUSION ===")
    print("- Outliers handled per year")  # summary of preprocessing step
    print("- Log transformation applied (variance stabilized)")
    print("- Differencing applied (trend removed)")
    print("- Data is now ready for SARIMA / ML models")

    return perMunicipality_df