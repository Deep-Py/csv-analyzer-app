import streamlit as st
import pandas as pd
import tempfile
import re
from difflib import get_close_matches

# -------------------------------
# CONFIG
# -------------------------------
REFERENCE_FILE_URL = "https://raw.githubusercontent.com/Deep-Py/csv-analyzer-app/main/reference.csv"


st.set_page_config(page_title="CSV Audit Assistant", layout="wide")
st.title("📊 CSV Audit Assistant")

# -------------------------------
# HELPERS
# -------------------------------
def clean_value(x):
    if pd.isna(x):
        return ""
    x = str(x).strip().upper().replace("\xa0", "")
    if x.endswith(".0"):
        x = x[:-2]
    if x.isdigit():
        x = str(int(x))
    return x


def get_suggestion(value, reference_list):
    matches = get_close_matches(value, reference_list, n=1, cutoff=0.5)
    if matches:
        return matches[0]
    for ref in reference_list:
        if value in ref or ref.startswith(value):
            return ref
    return "No suggestion"


# -------------------------------
# VALIDATION FUNCTION
# -------------------------------
def validate_pairs_from_github(excel_file):

    ref_df = pd.read_csv(REFERENCE_FILE_URL, dtype=str)

    ref_df["Vehicle"] = ref_df.iloc[:, 0].apply(clean_value)
    ref_df["Vehicle_ID"] = ref_df.iloc[:, 1].apply(clean_value)

    vehicle_to_id_map = {}
    for v, vid in zip(ref_df["Vehicle"], ref_df["Vehicle_ID"]):
        vehicle_to_id_map.setdefault(v, set()).add(vid)

    all_vehicles = list(vehicle_to_id_map.keys())

    df = pd.read_excel(excel_file, dtype=str)

    df["Value"] = df.iloc[:, 3].apply(clean_value)
    df["Published Value"] = df.iloc[:, 4].apply(clean_value)

    status, reason, suggestion, is_invalid = [], [], [], []

    for val, pub in zip(df["Value"], df["Published Value"]):

        if val not in vehicle_to_id_map:
            status.append("INVALID")
            reason.append("Spelling Error")
            suggestion.append(get_suggestion(val, all_vehicles))
            is_invalid.append(True)

        elif pub not in vehicle_to_id_mapexpected = ", ".join(vehicle_to_id_map[val])
            status.append("INVALID")
            reason.append(f"Mapping Error (Expected ID: {expected})")
            suggestion.append(val)
            is_invalid.append(True)

        else:
            status.append("VALID")
            reason.append("Correct Mapping")
            suggestion.append("")
            is_invalid.append(False)

    df["Status"] = status
    df["Reason"] = reason
    df["Suggestion"] = suggestion
    df["Is_Invalid"] = is_invalid

    # ✅ Auto-fix spelling
    fixed_df = df.copy()
    for i in fixed_df.index:
        if fixed_df.loc[i, "Reason"] == "Spelling Error":
            if fixed_df.loc[i, "Suggestion"] != "No suggestion":
                fixed_df.loc[i, "Value"] = fixed_df.loc[i, "Suggestion"]

    unique_pairs = df[["Value", "Published Value"]].drop_duplicates()

    valid_count = (df["Status"] == "VALID").sum()
    invalid_count = (df["Status"] == "INVALID").sum()

    spelling_err = (df["Reason"] == "Spelling Error").sum()
    mapping_err = df["Reason"].str.contains("Mapping Error").sum()

    return df, fixed_df, unique_pairs, valid_count, invalid_count, spelling_err, mapping_err


# -------------------------------
# UI
# -------------------------------
st.sidebar.header("🔍 Excel Validation")

excel_file = st.sidebar.file_uploader("Upload Excel File", type=["xlsx"])
validate_clicked = st.sidebar.button("Validate")

if validate_clicked and excel_file:

    df_val, fixed_df, unique_pairs, valid, invalid, spelling_err, mapping_err = validate_pairs_from_github(excel_file)

    st.subheader("✅ Validation Results")

    # ✅ Toggle with count
    show_invalid_only = st.toggle(f"Show Invalid Records ({invalid})")

    # ✅ Filter
    filter_option = st.selectbox(
        "Filter Records",
        ["All Records", "Spelling Errors", "Mapping Errors"]
    )

    display_df = df_val.copy()

    if show_invalid_only:
        display_df = display_df[display_df["Is_Invalid"]]

    if filter_option == "Spelling Errors":
        display_df = display_df[display_df["Reason"] == "Spelling Error"]

    elif filter_option == "Mapping Errors":
        display_df = display_df[display_df["Reason"].str.contains("Mapping Error")]

    # ✅ Highlight invalid rows
    def highlight_rows(row):
        if row["Is_Invalid"]:
            return ["background-color: #ffcccc"] * len(row)
        return [""] * len(row)

    if display_df.empty:
        st.warning("No records found")
    else:
        st.dataframe(display_df.style.apply(highlight_rows, axis=1), use_container_width=True)

    # ✅ SUMMARY
    st.subheader("📊 Summary")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Valid", valid)
        st.metric("Invalid", invalid)

    with col2:
        st.metric("Spelling Errors", spelling_err)
        st.metric("Mapping Errors", mapping_err)

    # ✅ EXPORT ERRORS
    st.subheader("⬇️ Export Errors")

    error_df = df_val[df_val["Is_Invalid"]]

    st.download_button(
        "Download Errors CSV",
        error_df.to_csv(index=False).encode("utf-8"),
        "errors.csv"
    )

    # ✅ AUTO FIX DOWNLOAD
    st.subheader("🛠️ Auto Fix")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        fixed_df.to_excel(tmp.name, index=False)
        fixed_file = open(tmp.name, "rb").read()

    st.download_button(
        "Download Corrected File",
        fixed_file,
        "corrected.xlsx"
    )

    # ✅ UNIQUE PAIRS
    st.subheader("🔹 Unique Pairs")
    st.dataframe(unique_pairs, use_container_width=True)


