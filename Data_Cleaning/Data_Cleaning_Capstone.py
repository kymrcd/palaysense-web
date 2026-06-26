import os
import pandas as pd  # Used for data manipulation
import re  # Used for cleaning text using patterns

# -----------------------------
# File paths
# -----------------------------
file_path = r"C:\Users\Juliana\Downloads\Capstone_Datasets.xlsx"  # Input file path
output_path = r"C:\Users\Juliana\Downloads\Capstone_Dataset_Cleaned_ML.xlsx"  # Output file path

# -----------------------------
# CLEANING FUNCTION
# -----------------------------
def run_cleaning(file_path, output_path):

    # -----------------------------
    # CHECK IF FILE EXISTS
    # -----------------------------
    if not os.path.exists(file_path):
        # If file does not exist, stop program and show error
        raise FileNotFoundError(f"Input file not found: {file_path}")

    # -----------------------------
    # LOAD ALL SHEETS
    # -----------------------------
    sheets = pd.read_excel(file_path, sheet_name=None)  # Read all sheets into dictionary
    print("Sheets in the file:", sheets.keys())  # Print sheet names

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

    # -----------------------------
    # NUMERIC COLUMNS
    # -----------------------------
    # List of columns expected to be numeric
    numeric_cols = [
        "production_irrigated", "production_rainfed", "production_total", "production_annual",
        "harvested_irrigated", "harvested_rainfed", "harvested_total", "harvested_annual",
        "fancy_palay_price", "other_variety_price", "quarterly_yield_mt_per_ha",
        "net_production_clean_rice_m_t_", "actual_consumption", "surplus_deficit",
    ]

    # Columns that should NOT have negative values
    non_negative_cols = [
        "production_irrigated", "production_rainfed", "production_total", "production_annual",
        "harvested_irrigated", "harvested_rainfed", "harvested_total", "harvested_annual",
        "fancy_palay_price", "other_variety_price",
        "actual_consumption"
    ]

    # -----------------------------
    # LOOP THROUGH EACH SHEET
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
        for col in ["fancy_palay_price", "other_variety_price"]:
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

        # For municipality data (year only)
        elif sheet_name == "Palay_Production_per_Municipali" and 'year' in df_cleaned.columns:
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
    # SAVE CLEANED DATA
    # -----------------------------
    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:

        # Save each cleaned sheet into one Excel file
        for sheet_name, df in cleaned_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"All cleaned sheets saved to: {output_path}")

    # -----------------------------
    # FINAL CHECK
    # -----------------------------
    # Check if file was successfully created
    if not os.path.exists(output_path):
        raise FileNotFoundError(f"Failed to save cleaned file: {output_path}")

    return output_path  # Return output file path