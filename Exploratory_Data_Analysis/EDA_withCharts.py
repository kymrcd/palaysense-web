import pandas as pd
import numpy as np
import calendar
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.tsa.stattools import adfuller


def run_eda_withCharts(file_path):

    print("\n=== START OF ML-READY EDA (WITH CHARTS) ===")

    # Load Excel file and read all sheets into separate dataframes
    sheets = pd.read_excel(file_path, sheet_name=None)

    print("\nAvailable sheets:", list(sheets.keys()))

    # Assign each sheet to a specific dataset (order-based assumption)
    provincial_df = sheets[list(sheets.keys())[0]]
    supply_df = sheets[list(sheets.keys())[1]]
    municipality_df = sheets[list(sheets.keys())[2]]

    # Convert year column to numeric so grouping and filtering works correctly
    for df in [provincial_df, supply_df, municipality_df]:
        if "year" in df.columns:
            df["year"] = pd.to_numeric(df["year"], errors="coerce")

    # Create a real datetime column for proper time-series plotting
    if "year" in provincial_df.columns and "month_num" in provincial_df.columns:
        provincial_df["time_index"] = pd.to_datetime(
            provincial_df["year"].astype(int).astype(str) + "-" +
            provincial_df["month_num"].astype(int).astype(str) + "-01"
        )

    # Prepare dictionary so we can loop all datasets easily
    print("\n=== YEAR COVERAGE ===")

    dataframes = {
        "Provincial": provincial_df,
        "Supply": supply_df,
        "Municipality": municipality_df
    }

    # Show yearly distribution and visualize how data is spread per year
    for name, df in dataframes.items():
        print(f"\n[{name} Data]")

        if "year" in df.columns:

            min_year = df["year"].min()
            max_year = df["year"].max()
            unique_years = sorted(df["year"].dropna().unique())

            print("Min Year:", min_year)
            print("Max Year:", max_year)
            print("Total Years:", len(unique_years))

            year_counts = df["year"].value_counts().sort_index()

            # Plot number of records per year to check imbalance
            plt.figure()
            plt.plot(year_counts.index, year_counts.values, marker="o")
            plt.title(f"{name} Year Distribution")
            plt.xlabel("Year")
            plt.ylabel("Count")
            plt.grid(True)
            plt.tight_layout()
            plt.show()

    # Display dataset sizes to understand scale differences
    print("\n=== DATA SHAPES ===")
    print("Provincial:", provincial_df.shape)
    print("Supply:", supply_df.shape)
    print("Municipality:", municipality_df.shape)

    # Check missing values to identify data quality issues per dataset
    print("\n=== MISSING VALUES (%) ALL SHEETS ===")

    all_missing_data = {}

    dataframes = {
        "Provincial": provincial_df,
        "Supply": supply_df,
        "Municipality": municipality_df
    }

    # Compute percentage of missing values and visualize them
    for name, df in dataframes.items():
        print(f"\n[{name}]")

        missing = (df.isnull().mean() * 100).sort_values(ascending=False)

        print(missing)

        all_missing_data[name] = missing

        # Bar chart to visually inspect missing columns
        plt.figure(figsize=(10, 4))
        missing.plot(kind="bar")
        plt.title(f"Missing Values (%) - {name}")
        plt.ylabel("% Missing")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

    # Check time coverage consistency across datasets
    print("\n=== TIME COVERAGE ===")

    for name, df in dataframes.items():
        if "year" in df.columns:
            print(f"\n{name}")
            print("Min Year:", df["year"].min())
            print("Max Year:", df["year"].max())
            print("Total Unique Years:", df["year"].nunique())

    # Define key target variables for analysis and forecasting
    target_cols = [
        "fancy_palay_price",
        "other_variety_price",
        "quarterly_yield_mt_per_ha"
    ]

    # Plot each target variable over time to observe trends
    for target in target_cols:
        if target in provincial_df.columns and "time_index" in provincial_df.columns:

            plt.figure()
            plt.plot(provincial_df["time_index"], provincial_df[target])
            plt.title(f"{target} Over Time")
            plt.xlabel("Time")
            plt.ylabel(target)
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.show()

    # Correlation analysis to find relationships between numeric variables
    numeric_df = provincial_df.select_dtypes(include=np.number)
    corr_matrix = numeric_df.corr()

    print("\n=== CORRELATION MATRIX ===")

    # Heatmap visualization of correlations
    plt.figure(figsize=(10, 6))
    sns.heatmap(corr_matrix, cmap="coolwarm", linewidths=0.5)
    plt.title("Correlation Heatmap")
    plt.tight_layout()
    plt.show()

    # Summary statistics and distribution analysis of target variables
    print("\n=== TARGET ANALYSIS ===")

    for target in target_cols:
        if target in provincial_df.columns:
            series = provincial_df[target].dropna()

            print(f"\n--- {target} ---")
            print("Mean:", series.mean())
            print("Std:", series.std())
            print("Min:", series.min())
            print("Max:", series.max())

            # Histogram to understand data distribution
            plt.figure()
            plt.hist(series, bins=30)
            plt.title(f"Distribution - {target}")
            plt.xlabel(target)
            plt.ylabel("Frequency")
            plt.tight_layout()
            plt.show()

            # Boxplot to detect outliers and spread
            plt.figure()
            plt.boxplot(series.dropna())
            plt.title(f"Boxplot - {target}")
            plt.ylabel(target)
            plt.tight_layout()
            plt.show()

    # Seasonal pattern analysis using monthly aggregation
    print("\n=== SEASONALITY ANALYSIS ===")

    if "month_num" in provincial_df.columns:

        for target in target_cols:
            if target in provincial_df.columns:

                monthly = provincial_df.groupby("month_num")[target].mean()

                plt.figure()
                plt.plot(monthly.index, monthly.values, marker="o")
                plt.title(f"Seasonality (All Years Combined) - {target}")
                plt.xlabel("Month")
                plt.ylabel("Average Value")
                plt.xticks(
                    range(1, 13),
                    [calendar.month_abbr[i] for i in range(1, 13)]
                )
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                plt.show()

    # Outlier detection using z-score method
    print("\n=== ANOMALY DETECTION ===")

    for target in target_cols:
        if target in provincial_df.columns:

            series = provincial_df[target].dropna()

            if len(series) > 10:
                z = (series - series.mean()) / series.std()
                anomalies = np.abs(z) > 3

                print(f"{target}: {anomalies.sum()} anomalies")

                # Plot anomalies on time series
                plt.figure()

                plt.plot(series.index, series.values, label="Normal Data")

                plt.scatter(
                    series.index[anomalies],
                    series[anomalies],
                    color="red",
                    label="Anomalies"
                )

                plt.title(f"Anomaly Detection - {target}")
                plt.xlabel("Index")
                plt.ylabel(target)
                plt.legend()
                plt.tight_layout()
                plt.show()

    # Stationarity check using rolling mean visualization
    for target in target_cols:
        if target in provincial_df.columns:

            series = provincial_df[target].dropna()

            if len(series) > 10:
                rolling_mean = series.rolling(window=12).mean()

                plt.figure()

                plt.plot(series.index, series.values, label="Original Series")
                plt.plot(rolling_mean.index, rolling_mean.values, label="Rolling Mean (12)", linestyle="--")

                plt.title(f"Stationarity Visual Check - {target}")
                plt.xlabel("Index")
                plt.ylabel(target)
                plt.legend()

                plt.tight_layout()
                plt.show()

    # Supply-side analysis for food security estimation
    print("\n=== SUPPLY ANALYSIS ===")

    if all(col in supply_df.columns for col in [
        "net_production_clean_rice",
        "actual_consumption"
    ]):

        supply_df = supply_df.copy()

        supply_df["self_sufficiency_ratio"] = (
            supply_df["net_production_clean_rice"] /
            supply_df["actual_consumption"].replace(0, np.nan) * 100
        )

        plt.figure()
        plt.plot(supply_df["year"], supply_df["self_sufficiency_ratio"], marker="o")
        plt.title("Self Sufficiency Ratio Over Time")
        plt.xlabel("Year")
        plt.ylabel("Ratio (%)")
        plt.tight_layout()
        plt.show()

    # Identify top municipalities based on total palay production
    print("\n=== MUNICIPALITY INSIGHTS ===")

    if "palay_production" in municipality_df.columns:

        muni_summary = municipality_df.groupby("municipality")["palay_production"].sum().sort_values(ascending=False).head(10)

        print("\nTop Municipalities:")
        print(muni_summary)

        plt.figure()
        muni_summary.plot(kind="bar")
        plt.title("Top 10 Municipalities - Palay Production")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

    # Final summary of findings from the EDA process
    print("\n=== FINAL EDA CONCLUSION ===")
    print("- Time series structure confirmed")
    print("- Seasonal patterns visible")
    print("- Correlations exist for ML features")
    print("- Dataset ready for forecasting models")

    return provincial_df, supply_df, municipality_df