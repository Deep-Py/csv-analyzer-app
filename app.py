import streamlit as st
import pandas as pd
import tempfile
import re
from difflib import get_close_matches

# ===============================
# CONFIG
# ===============================
REFERENCE_FILE_URL = "https://raw.githubusercontent.com/Deep-Py/csv-analyzer-app/main/reference.csv"

st.set_page_config(page_title="CSV Audit Assistant", layout="wide")

st.title("CSV Audit Assistant")

# ===============================
# HELPERS
# ===============================
def clean_value(x):
    if pd.isna(x):
        return ""
    x = str(x).strip().upper()
    if x.endswith(".0"):
        x = x[:-2]
    if x.isdigit():
        x = str(int(x))
    return x


def get_suggestion(value, reference_list):
    match = get_close_matches(value, reference_list, n=1, cutoff=0.5)
    if match:
        return match[0]

    for ref in reference_list:
        if value in ref or ref.startswith(value):
            return ref

    return "No suggestion"


# ===============================
# CSV ANALYZER
# ===============================
def process_csv(file):
    df = pd.read_csv(file)
    col = df.iloc[:, 0].dropna()
    return len(col), col.nunique()


def generate_summary(results):
    added, deleted = [], []

    for f in results:
        name = f["File Name"].upper()

        if re.search(r'(^|_)ADD($|_)', name):
            added.append(f)
        elif re.search(r'(^|_)DELETE($|_)|(^|_)REMOVE($|_)', name):
            deleted.append(f)

    def get_domain(name):
        name = name.upper()
        if "EZ_ADDT_RESTR" in name:
            return "EZ_ADDT_RESTR"
        elif "EZ_TIME_RESTR" in name:
            return "EZ_TIME_RESTR"
        elif "EZ_RESTR" in name:
            return "EZ_RESTR"
        return name

    total_added = sum(x["Total"] for x in added)
    total_deleted = sum(x["Total"] for x in deleted)

    text = "MMT Updates Completed:\n\n"

    if added:
        text += "Added Records:\n"
        for f in added:
            text += f"  • {f['Total']} records added into {get_domain(f['File Name'])}\n"
        text += "\n"

    if deleted:
        text += "Deleted Records:\n"
        for f in deleted:
            text += f"  • {f['Total']} records deleted from {get_domain(f['File Name'])}\n"
        text += "\n"

    text += f"Summary:\n  • Total Added: {total_added}\n  • Total Deleted: {total_deleted}\n\nThanks,\nDeepesh Pawar"

    return text


# ===============================
# VALIDATION ENGINE
# ===============================
def validate_pairs(file):

    ref = pd.read_csv(REFERENCE_FILE_URL, dtype=str)

    ref["Vehicle"] = ref.iloc[:, 0].apply(clean_value)
    ref["Vehicle_ID"] = ref.iloc[:, 1].apply(clean_value)

    vehicle_map = {}
    for v, vid in zip(ref["Vehicle"], ref["Vehicle_ID"]):
        vehicle_map.setdefault(v, set()).add(vid)

    vehicles = list(vehicle_map.keys())

    df = pd.read_excel(file, dtype=str)

    df["Value"] = df.iloc[:, 3].apply(clean_value)
    df["Published Value"] = df.iloc[:, 4].apply(clean_value)

    status = []
    reason = []
    suggestion = []
    is_invalid = []

    for val, pub in zip(df["Value"], df["Published Value"]):

        if val not in vehicle_map:
            status.append("INVALID")
            reason.append("Spelling Error")
            suggestion.append(get_suggestion(val, vehicles))
            is_invalid.append(True)

        else:
            expected = vehicle_map[val]

            if pub not in expected:
                status.append("INVALID")
                reason.append(f"Mapping Error (Expected: {', '.join(expected)})")
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

    # Auto fix (only spelling)
    fixed_df = df.copy()
    for i in fixed_df.index:
        if fixed_df.loc[i, "Reason"] == "Spelling Error":
            if fixed_df.loc[i, "Suggestion"] != "No suggestion":
                fixed_df.loc[i, "Value"] = fixed_df.loc[i, "Suggestion"]

    # Metrics
    valid = (df["Status"] == "VALID").sum()
    invalid = (df["Status"] == "INVALID").sum()
    spelling = (df["Reason"] == "Spelling Error").sum()
    mapping = df["Reason"].str.contains("Mapping Error").sum()

    unique_pairs = df[["Value", "Published Value"]].drop_duplicates()

    return df, fixed_df, unique_pairs, valid, invalid, spelling, mapping, vehicle_map


# ===============================
# TABS
# ===============================
tab1, tab2 = st.tabs(["CSV Analyzer", "Excel Validation"])

# ===============================
# TAB 1 → CSV ANALYZER
# ===============================
with tab1:

    files = st.file_uploader("Upload CSV files", type=["csv"], accept_multiple_files=True)

    if files:
        results = []

        for f in files:
            total, unique = process_csv(f)

            results.append({
                "File Name": f.name,
                "Total": total,
                "Unique": unique
            })

        df = pd.DataFrame(results)

        st.subheader("Results")
        st.dataframe(df, use_container_width=True)

        st.subheader("Generated Summary")
        st.text_area("", generate_summary(results), height=250)

# ===============================
# TAB 2 → VALIDATION
# ===============================
with tab2:

    excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])

    
if excel_file:

    df, fixed_df, unique_pairs, valid, invalid, spelling, mapping, vehicle_map = validate_pairs(excel_file)

    # ✅ Toggle
    show_invalid = st.toggle(f"Show Invalid Records ({invalid})")

    display = df.copy()

    if show_invalid:
        display = display[display["Is_Invalid"] == True]

    display = display.reset_index(drop=True)

    # ✅ TABLE
    st.subheader("Validation Results")

    def highlight(row):
        if row["Is_Invalid"]:
            return ["background-color: #ffe6e6"] * len(row)
        return [""] * len(row)

    st.dataframe(display.style.apply(highlight, axis=1), use_container_width=True)

    # ✅ SUMMARY
    st.subheader("Summary")

    col1, col2 = st.columns(2)

    col1.metric("Valid", valid)
    col1.metric("Invalid", invalid)

    col2.metric("Spelling Errors", spelling)
    col2.metric("Mapping Errors", mapping)

    # ✅ AUTO FIX BUTTON
    st.subheader("🛠️ Auto Fix")

    if st.button("Apply Auto Fix"):

        # ✅ Start from ORIGINAL file (VERY IMPORTANT)
        original_df = pd.read_excel(excel_file, dtype=str)

        corrected_df = original_df.copy()

        for i in range(len(df)):

            if df.loc[i, "Reason"] == "Spelling Error":

                suggestion = df.loc[i, "Suggestion"]

                if suggestion != "No suggestion":
                    corrected_df.iloc[i, 3] = suggestion

            elif "Mapping Error" in df.loc[i, "Reason"]:

                val = df.loc[i, "Value"]

                # ✅ Get correct ID from reference
                for v, ids in vehicle_map.items():
                    if v == val:
                        corrected_df.iloc[i, 4] = list(ids)[0]

        # ✅ Save clean file (no extra columns)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            corrected_df.to_excel(tmp.name, index=False)
            clean_file = open(tmp.name, "rb").read()

        st.success("✅ Auto Fix Applied")

        st.download_button(
            "Download Corrected Clean File",
            clean_file,
            "corrected_clean.xlsx"
        )

    # ✅ EXPORT ONLY ERRORS
    st.subheader("⬇️ Export Errors")

    error_df = df[df["Is_Invalid"] == True]

    st.download_button(
        "Download Errors",
        error_df.to_csv(index=False),
        "errors.csv"
    )

    # ✅ UNIQUE PAIRS
    st.subheader("Unique Pairs")
    st.dataframe(unique_pairs, use_container_width=True)



