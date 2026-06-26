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
# MAIN EDA FUNCTION
# -----------------------------
def run_eda(file_path):

    print("\n=== START OF ML-READY EDA ===")

    # load Excel file with multiple sheets into dictionary of DataFrames
    sheets = pd.read_excel(file_path, sheet_name=None)

    # assign each sheet to a specific dataframe
    provincial_df = sheets[list(sheets.keys())[0]]
    supply_df = sheets[list(sheets.keys())[1]]
    municipality_df = sheets[list(sheets.keys())[2]]

    # convert year column to numeric for consistency
    for df in [provincial_df, supply_df, municipality_df]:
        if "year" in df.columns:
            df["year"] = pd.to_numeric(df["year"], errors="coerce")

    # sort data chronologically for correct time-series ordering
    if "month_num" in provincial_df.columns:
        provincial_df = provincial_df.sort_values(["year", "month_num"])

    # -----------------------------
    # DATA OVERVIEW
    # -----------------------------
    print("\n=== DATA SHAPES ===")
    print("Provincial:", provincial_df.shape)  # dataset size (rows, columns)
    print("Supply:", supply_df.shape)
    print("Municipality:", municipality_df.shape)

    # -----------------------------
    # MISSING VALUES
    # -----------------------------
    print("\n=== MISSING VALUES (%) ===")

    for name, df in {
        "Provincial": provincial_df,
        "Supply": supply_df,
        "Municipality": municipality_df
    }.items():

        print(f"\n[{name}]")
        print((df.isnull().mean() * 100).sort_values(ascending=False).head(10))  # top missing columns

    # -----------------------------
    # TIME COVERAGE
    # -----------------------------
    print("\n=== TIME COVERAGE ===")

    for name, df in {
        "Provincial": provincial_df,
        "Supply": supply_df,
        "Municipality": municipality_df
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
        "fancy_palay_price",
        "other_variety_price",
        "quarterly_yield_mt_per_ha"
    ]

    # apply outlier handling per year for selected targets
    provincial_df = handle_outliers_per_year(provincial_df, target_cols)

    # apply stationarity transformation (log + differencing)
    provincial_df = make_stationary(provincial_df, target_cols)

    # -----------------------------
    # TARGET STATISTICS
    # -----------------------------
    print("\n=== TARGET ANALYSIS (PER YEAR) ===")

    for target in target_cols:
        if target in provincial_df.columns:
            print(f"\n--- {target} ---")
            print(
                provincial_df.groupby("year")[target]
                .agg(["mean", "std", "min", "max"])  # summary statistics per year
                .tail(10)
            )

    # -----------------------------
    # STATIONARITY TEST (ADF)
    # -----------------------------
    print("\n=== STATIONARITY TEST ===")

    for target in target_cols:

        diff_col = f"{target}_log_diff"

        if diff_col in provincial_df.columns:

            s = provincial_df[diff_col].dropna()  # remove NaNs before testing

            if len(s) > 10:  # ensure enough data points for ADF test
                result = adfuller(s)  # perform Augmented Dickey-Fuller test

                print(f"\n{target} (after transformation)")
                print("ADF:", result[0])  # test statistic
                print("p-value:", result[1])  # significance level

                if result[1] < 0.05:
                    print("Stationary")  # reject null hypothesis
                else:
                    print("Still Non-stationary")  # fail to reject null hypothesis

    # -----------------------------
    # FINAL CONCLUSION
    # -----------------------------
    print("\n=== FINAL CONCLUSION ===")
    print("- Outliers handled per year")  # summary of preprocessing step
    print("- Log transformation applied (variance stabilized)")
    print("- Differencing applied (trend removed)")
    print("- Data is now ready for SARIMA / ML models")

    return provincial_df, supply_df, municipality_df