import os

#Import eda with charts
from Exploratory_Data_Analysis.EDA_withCharts import run_eda_withCharts

#START
file_path = r"C:\Users\Juliana\Downloads\Capstone_Datasets.xlsx"
output_path = r"C:\Users\Juliana\Downloads\Capstone_Dataset_Cleaned_ML.xlsx"

# -----------------------------
# CONDITIONAL CLEANING
# -----------------------------
if os.path.exists(output_path):
    print(f"Cleaned file already exists: {output_path}")
else:
    print(f"Cleaned file not found. Running cleaning from raw dataset: {file_path}")
    from Data_Cleaning.Data_Cleaning_Capstone import run_cleaning
    run_cleaning(file_path, output_path)

# -----------------------------
# RUN EDA with charts
# -----------------------------
provincial_df, supply_df, municipality_df = run_eda_withCharts(output_path)

