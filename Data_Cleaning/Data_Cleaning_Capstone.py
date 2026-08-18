import os
import pandas as pd  # Used for data manipulation
import re  # Used for cleaning text using patterns
import tempfile
import openpyxl

# -----------------------------
# File paths
# -----------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

file_path = os.path.join(BASE_DIR, "data", "Master", "provincial_raw.xlsx")
output_path = os.path.join(BASE_DIR, "data", "Master",  "provincial_cleaned.xlsx")

file_path2 = os.path.join(BASE_DIR, "data", "Master",  "municipality_raw.xlsx")
output_path2 = os.path.join(BASE_DIR, "data",  "Master", "municipality_cleaned.xlsx")

# -----------------------------
# CLEANING FUNCTION
# -----------------------------
def run_cleaning(file_path,
    output_path,
    file_path2,
    output_path2,
    clean_provincial=True,
    clean_municipality=True):

    # -----------------------------
    # CHECK IF FILE EXISTS
    # -----------------------------
    if clean_provincial and not os.path.exists(file_path):
        raise FileNotFoundError(f"Input file not found: {file_path}")

    if clean_municipality and not os.path.exists(file_path2):
        raise FileNotFoundError(f"Input file not found: {file_path2}")

    # -----------------------------
    # LOAD ALL SHEETS
    # -----------------------------
    # Provincial
    sheets = {}
    sheets2 = {}

    if clean_provincial:
        sheets = pd.read_excel(file_path, sheet_name=None, engine='openpyxl')
        print("Provincial Sheets:", sheets.keys())

    # Municipality
    if clean_municipality:
        sheets2 = pd.read_excel(file_path2, sheet_name=None, engine='openpyxl')
        print("Municipality Sheets:", sheets2.keys())

    # -----------------------------
    # FUNCTION: CLEAN COLUMN NAMES
    # -----------------------------
    def clean_column_names(columns):
        cleaned_columns = []  # List to store cleaned column names

        for col in columns:  # Loop through each column name
            col = str(col).strip().lower().replace(" ", "_")  # Lowercase, remove spaces, replace space with underscore
            col = re.sub(r"[^\w]", "", col)  # Remove special characters
            cleaned_columns.append(col)  # Add cleaned name to list

        return cleaned_columns  # Return cleaned column names

    # Dictionary to store cleaned sheets
    cleaned_sheets = {}
    cleaned_sheets2 = {}

    # -----------------------------
    # NUMERIC COLUMNS
    # -----------------------------
    # List of columns expected to be numeric
    numeric_cols = [
        "production_irrigated", "production_rainfed", "production_total", "production_annual",
        "harvested_irrigated", "harvested_rainfed", "harvested_total", "harvested_annual",
        "fancy_palay_price", "other_variety_price", "quarterly_yield_mt_per_ha",
        "net_production_clean_rice_m_t_", "actual_consumption", "surplus_deficit"
    ]

    numeric_cols2 = [
        "hybridpremium_dry", "hybridpremium_wet", "hybridordinary_dry", "hybridordinary_wet", "inbredpremium_dry",
        "inbredpremium_wet", "inbredordinary_dry", "inbredordinary_wet"
    ]

    # Columns that should NOT have negative values
    non_negative_cols = [
        "production_irrigated", "production_rainfed", "production_total", "production_annual",
        "harvested_irrigated", "harvested_rainfed", "harvested_total", "harvested_annual",
        "fancy_palay_price", "other_variety_price", "actual_consumption"
    ]

    non_negative_cols2 = [
        "hybridpremium_dry", "hybridpremium_wet", "hybridordinary_dry", "hybridordinary_wet", "inbredpremium_dry",
        "inbredpremium_wet", "inbredordinary_dry", "inbredordinary_wet"
    ]

    # -----------------------------
    # LOOP THROUGH EACH SHEET (PROVINCIAL)
    # -----------------------------
    for sheet_name, df in sheets.items():

        # Copy original data to avoid modifying it directly
        df_cleaned = df.copy()

        # -----------------------------
        # 1. CLEAN COLUMN NAMES
        # -----------------------------
        df_cleaned.columns = clean_column_names(df_cleaned.columns)

        # -----------------------------
        # 2. CONVERT NUMERIC COLUMNS
        # -----------------------------
        for col in numeric_cols:
            if col in df_cleaned.columns:

                # Convert column to numeric safely
                df_cleaned[col] = pd.to_numeric(
                    df_cleaned[col]
                    .astype(str)  # Convert to string first
                    .str.replace(",", "")  # Remove commas
                    .replace("nan", None),  # Replace string "nan" with None
                    errors="coerce"  # Invalid values become NaN
                )

                # Remove negative values ONLY for selected columns
                if col in non_negative_cols:
                    df_cleaned[col] = df_cleaned[col].clip(lower=0)

        # -----------------------------
        # 3. HANDLE MISSING VALUES
        # -----------------------------
        for col in ["fancy_palay_price", "other_variety_price", "quarterly_yield_mt_per_ha"]:
            if col in df_cleaned.columns:

                # Fill missing values using linear interpolation then forward fill
                df_cleaned[col] = df_cleaned[col].interpolate(method="linear").ffill()

        # -----------------------------
        # 3b. FILL ANY REMAINING MISSING VALUES
        # -----------------------------
        for col in ["fancy_palay_price", "other_variety_price", "quarterly_yield_mt_per_ha"]:
            if col in df_cleaned.columns:

                # Fill remaining missing values using forward and backward fill
                df_cleaned[col] = df_cleaned[col].ffill().bfill()

        # -----------------------------
        # 4. STANDARDIZE STRINGS
        # -----------------------------
        for col in ["province", "month"]:
            if col in df_cleaned.columns:

                # Convert to string, remove spaces, make lowercase
                df_cleaned[col] = df_cleaned[col].astype(str).str.strip().str.lower() #Manila -> manila

        # -----------------------------
        # 5. CREATE DATE COLUMN
        # -----------------------------
        # If year and month exist, create full date
        if 'year' in df_cleaned.columns and 'month_num' in df_cleaned.columns:
            df_cleaned["date"] = pd.to_datetime(
                df_cleaned["year"].astype(str) + "-" +
                df_cleaned["month_num"].astype(str) + "-01"
            )

        # For Palay_Sufficiency_Bataan (year only)
        elif sheet_name == "Palay_Sufficiency_Bataan" and 'year' in df_cleaned.columns:
            df_cleaned["date"] = pd.to_datetime(
                df_cleaned["year"].astype(str) + "-12-01"
            )

        # For municipality data (year only) - case-insensitive and partial match
        elif ('year' in df_cleaned.columns and
              sheet_name.lower().replace(" ", "").replace("_", "").replace("-", "") in
              ["palayproductionpermunicipali", "palayproductionpermunicipality"]):
            df_cleaned["date"] = pd.to_datetime(
                df_cleaned["year"].astype(str) + "-12-01"
            )

        # -----------------------------
        # SORT DATA BY DATE
        # -----------------------------
        if "date" in df_cleaned.columns:

            # Sort rows by date and reset index
            df_cleaned = df_cleaned.sort_values("date").reset_index(drop=True)

        # -----------------------------
        # 6. REMOVE DUPLICATES
        # -----------------------------
        df_cleaned = df_cleaned.drop_duplicates()

        # Save cleaned sheet to dictionary
        cleaned_sheets[sheet_name] = df_cleaned

    # -----------------------------
    # LOOP THROUGH EACH SHEET (MUNICIPALITY)
    # -----------------------------
    for sheet_name2, df2 in sheets2.items():
        # Copy original data to avoid modifying it directly
        df_cleaned2 = df2.copy()

        # -----------------------------
        # 1. CLEAN COLUMN NAMES
        # -----------------------------
        df_cleaned2.columns = clean_column_names(df_cleaned2.columns)

        # Fix misspelled column names (handle both "municpality" and "municipality" variants)
        df_cleaned2.rename(
            columns={"municpality": "municipality"},
            inplace=True
        )
        # Merge duplicate "municipality" column values before dropping duplicates.
        # The raw municipality data has both 'municipality' (lowercase, has data)
        # and 'Municipality' (uppercase, mostly NaN but has values in later rows).
        # After clean_column_names(), both become 'municipality'. The
        # duplicated() below keeps the LAST column (originally uppercase) which
        # is mostly empty, causing thousands of missing municipality names.
        muni_cols = [c for c in df_cleaned2.columns if c == "municipality"]
        if len(muni_cols) > 1:
            for dup_col in muni_cols[1:]:
                df_cleaned2[muni_cols[0]] = df_cleaned2[muni_cols[0]].fillna(df_cleaned2[dup_col])
        # Also handle duplicate "month" columns the same way
        month_cols = [c for c in df_cleaned2.columns if c == "month"]
        if len(month_cols) > 1:
            for dup_col in month_cols[1:]:
                df_cleaned2[month_cols[0]] = df_cleaned2[month_cols[0]].fillna(df_cleaned2[dup_col])
        # Handle duplicate columns caused by misspelled + correct column names,
        # or columns like "Month " and "Month" both becoming "month".
        # Duplicate columns cause df_cleaned2[col] to return a DataFrame instead
        # of a Series, which breaks .str accessor with:
        #   'DataFrame' object has no attribute 'str'
        df_cleaned2 = df_cleaned2.loc[:, ~df_cleaned2.columns.duplicated()]

        # -----------------------------
        # 2. CONVERT NUMERIC COLUMNS
        # -----------------------------
        for col in numeric_cols2:
            if col in df_cleaned2.columns:

                # Convert column to numeric safely
                df_cleaned2[col] = pd.to_numeric(
                    df_cleaned2[col]
                    .astype(str)  # Convert to string first
                    .str.replace(",", "")  # Remove commas
                    .replace("nan", None),  # Replace string "nan" with None
                    errors="coerce"  # Invalid values become NaN
                )

                # Remove negative values ONLY for selected columns
                if col in non_negative_cols2:
                    df_cleaned2[col] = df_cleaned2[col].clip(lower=0)

        # -----------------------------
        # 3. HANDLE MISSING VALUES
        # -----------------------------
        for col in ["hybridpremium_dry", "hybridpremium_wet", "hybridordinary_dry", "hybridordinary_wet",
                    "inbredpremium_dry", "inbredpremium_wet", "inbredordinary_dry", "inbredordinary_wet"]:
            if col in df_cleaned2.columns:
                # Fill missing values using linear interpolation then forward fill
                df_cleaned2[col] = df_cleaned2[col].interpolate(method="linear").ffill()

        # -----------------------------
        # 3b. FILL ANY REMAINING MISSING VALUES
        # -----------------------------
        for col in ["hybridpremium_dry", "hybridpremium_wet", "hybridordinary_dry", "hybridordinary_wet",
                    "inbredpremium_dry", "inbredpremium_wet", "inbredordinary_dry", "inbredordinary_wet"]:
            if col in df_cleaned2.columns:
                # Fill remaining missing values using forward and backward fill
                df_cleaned2[col] = df_cleaned2[col].ffill().bfill()

        # -----------------------------
        # 4. STANDARDIZE STRINGS
        # -----------------------------
        for col in ["municipality", "month"]:
            if col in df_cleaned2.columns:
                # Convert to string, remove spaces, make lowercase
                df_cleaned2[col] = df_cleaned2[col].astype(str).str.strip().str.lower()  # Balanga -> balanga

        # -----------------------------
        # 4b. NORMALIZE MUNICIPALITY NAMES (remove duplicates like "balanga" and "balanga city")
        # -----------------------------
        if "municipality" in df_cleaned2.columns:
            # Map "balanga" -> "balanga city" to standardize
            df_cleaned2["municipality"] = df_cleaned2["municipality"].replace(
                {"balanga": "balanga city", "balanga city": "balanga city"}
            )
            # Remove string "nan"/"none" artifacts from .astype(str) conversion
            df_cleaned2["municipality"] = df_cleaned2["municipality"].replace(
                ["nan", "none", "nat", "na"], None
            )

        # -----------------------------
        # 5. CREATE DATE COLUMN
        # -----------------------------
        # If year and month exist, create full date
        if 'year' in df_cleaned2.columns and 'month_num' in df_cleaned2.columns:
            df_cleaned2["date"] = pd.to_datetime(
                df_cleaned2["year"].astype(str) + "-" +
                df_cleaned2["month_num"].astype(str) + "-01"
            )

        # -----------------------------
        # SORT DATA BY DATE
        # -----------------------------
        if "date" in df_cleaned2.columns:
            # Sort rows by date and reset index
            df_cleaned2 = df_cleaned2.sort_values("date").reset_index(drop=True)

        # -----------------------------
        # 5b. FORWARD-FILL municipality AND month AFTER sorting by date
        # -----------------------------
        # Group by year and forward-fill missing municipality/month values
        # This ensures rows with missing labels inherit from the previous valid row
        for col in ["municipality", "month"]:
            if col in df_cleaned2.columns:
                if "year" in df_cleaned2.columns:
                    df_cleaned2[col] = df_cleaned2.groupby("year")[col].transform(
                        lambda s: s.ffill()
                    )

        # -----------------------------
        # 6. REMOVE DUPLICATES
        # -----------------------------
        df_cleaned2 = df_cleaned2.drop_duplicates()

        # -----------------------------
        # 6b. DROP ROWS WHERE MUNICIPALITY OR MONTH IS STILL EMPTY
        # -----------------------------
        # After forward-fill, drop any remaining rows where these key identifiers
        # are still missing (e.g., first row of a year group with no predecessor)
        df_cleaned2 = df_cleaned2.dropna(subset=["municipality", "month"])

        # Normalize sheet name: treat "Sheet1" as "Municipality_Data"
        # so both "Sheet1" and "Municipality_Data" sheet names are accepted
        output_sheet_name = sheet_name2
        if output_sheet_name.strip().lower() == "sheet1":
            output_sheet_name = "Municipality_Data"
        cleaned_sheets2[output_sheet_name] = df_cleaned2

    # -----------------------------
    # SAVE CLEANED DATA
    # -----------------------------
    def _coerce_to_dataframe(obj):
        """
        Defensive coercion to avoid:
          'list' object has no attribute 'to_excel'
        when a sheet unexpectedly becomes a list (e.g., list of dfs).
        """
        if obj is None:
            return None
        if isinstance(obj, pd.DataFrame):
            return obj
        if isinstance(obj, list):
            # If list contains DataFrames, concatenate them
            dfs = [x for x in obj if isinstance(x, pd.DataFrame)]
            if not dfs:
                return None
            return pd.concat(dfs, ignore_index=True)
        return None

    # =========================
    # SAVE PROVINCIAL CLEANED DATA
    # =========================
    if cleaned_sheets:

        temp_output = output_path + ".tmp.xlsx"

        with pd.ExcelWriter(temp_output, engine="openpyxl") as writer:
            for sheet_name, df in cleaned_sheets.items():

                df_out = _coerce_to_dataframe(df)

                if df_out is None:
                    print(f"[WARN] Skipping provincial sheet '{sheet_name}'")
                    continue

                df_out.to_excel(
                    writer,
                    sheet_name=sheet_name,
                    index=False
                )

        # Verify the generated Excel
        openpyxl.load_workbook(temp_output)

        # Replace only if successful
        os.replace(temp_output, output_path)

        print(f"All cleaned provincial sheets saved to: {output_path}")

    else:
        print("[SKIP] No provincial data to save.")

    # =========================
    # SAVE MUNICIPAL CLEANED DATA
    # =========================
    if cleaned_sheets2:

        temp_output = output_path2 + ".tmp.xlsx"

        with pd.ExcelWriter(temp_output, engine="openpyxl") as writer:
            for sheet_name2, df2 in cleaned_sheets2.items():

                df_out2 = _coerce_to_dataframe(df2)

                if df_out2 is None:
                    print(f"[WARN] Skipping municipal sheet '{sheet_name2}'")
                    continue

                df_out2.to_excel(
                    writer,
                    sheet_name=sheet_name2,
                    index=False
                )

        # Verify the generated Excel
        openpyxl.load_workbook(temp_output)

        # Replace only if successful
        os.replace(temp_output, output_path2)

        print(f"All cleaned municipal sheets saved to: {output_path2}")

    else:
        print("[SKIP] No municipal data to save.")

    # -----------------------------
    # ALSO SAVE TO data/cleaned/ FOR DASHBOARD CONSUMPTION
    # -----------------------------
    dashboard_clean_dir = os.path.join(BASE_DIR, "data", "cleaned")
    os.makedirs(dashboard_clean_dir, exist_ok=True)

    if cleaned_sheets:
        prov_dashboard_path = os.path.join(dashboard_clean_dir, "provincial_cleaned.xlsx")
        with pd.ExcelWriter(prov_dashboard_path, engine='openpyxl') as writer:
            for sheet_name, df in cleaned_sheets.items():
                df_out = _coerce_to_dataframe(df)
                if df_out is not None:
                    df_out.to_excel(writer, sheet_name=sheet_name, index=False)
        print(f"[Data_Cleaning] Provincial dashboard-ready -> {prov_dashboard_path}")

    if cleaned_sheets2:
        muni_dashboard_path = os.path.join(dashboard_clean_dir, "municipality_cleaned.xlsx")
        with pd.ExcelWriter(muni_dashboard_path, engine='openpyxl') as writer:
            for sheet_name2, df2 in cleaned_sheets2.items():
                df_out2 = _coerce_to_dataframe(df2)
                if df_out2 is not None:
                    df_out2.to_excel(writer, sheet_name=sheet_name2, index=False)
        print(f"[Data_Cleaning] Municipality dashboard-ready -> {muni_dashboard_path}")

    # -----------------------------
    # FINAL CHECK
    # -----------------------------
    if clean_provincial and not os.path.exists(output_path):
        raise FileNotFoundError(f"Failed to save cleaned file: {output_path}")

    if clean_municipality and not os.path.exists(output_path2):
        raise FileNotFoundError(f"Failed to save cleaned file: {output_path2}")

    return output_path, output_path2

if __name__ == "__main__":
    run_cleaning(file_path, output_path, file_path2, output_path2)
