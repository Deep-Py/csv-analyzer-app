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
# SESSION STATE
# ===============================
if "auto_fixed" not in st.session_state:
    st.session_state.auto_fixed = False
if "corrected_pairs" not in st.session_state:
    st.session_state.corrected_pairs = None
if "original_df" not in st.session_state:
    st.session_state.original_df = None

# ===============================
# CACHED DATA
# ===============================
@st.cache_data
def load_reference():
    return pd.read_csv(REFERENCE_FILE_URL, dtype=str)


@st.cache_data
def validate_pairs(file_bytes):

    ref = load_reference()

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
        matches = get_close_matches(value, reference_list, n=1, cutoff=0.5)
        if matches:
            return matches[0]
        for ref_val in reference_list:
            if value in ref_val:
                return ref_val
        return "No suggestion"

    # ✅ Prepare reference
    ref["Vehicle"] = ref.iloc[:, 0].apply(clean_value)
    ref["Vehicle_ID"] = ref.iloc[:, 1].apply(clean_value)

    vehicle_map = {}
    for v, vid in zip(ref["Vehicle"], ref["Vehicle_ID"]):
        vehicle_map.setdefault(v, set()).add(vid)

    vehicles = list(vehicle_map.keys())

    # ✅ Read Excel
    df = pd.read_excel(file_bytes, dtype=str)

    df["Value"] = df.iloc[:, 3].apply(clean_value)
    df["Published Value"] = df.iloc[:, 4].apply(clean_value)

    status, reason, suggestion, is_invalid = [], [], [], []

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

    unique_pairs = df[["Value", "Published Value", "Is_Invalid"]].drop_duplicates()

    return df, unique_pairs, vehicle_map


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

    text = "MMT Updates Completed:\n\n"

    for f in added:
        text += f"Added: {f['Total']} from {f['File Name']}\n"

    for f in deleted:
        text += f"Deleted: {f['Total']} from {f['File Name']}\n"

    return text


# ===============================
# UI TABS
# ===============================
tab1, tab2 = st.tabs(["CSV Analyzer", "Excel Validation"])

# ===============================
# CSV TAB
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

        df_res = pd.DataFrame(results)
        st.dataframe(df_res)

        st.text_area("Summary", generate_summary(results), height=200)

# ===============================
# VALIDATION TAB
# ===============================
with tab2:

    excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])

    if excel_file:

        file_bytes = excel_file.getvalue()

        df, unique_pairs, vehicle_map = validate_pairs(file_bytes)

        # ✅ Cache original Excel ONCE
        if st.session_state.original_df is None:
            st.session_state.original_df = pd.read_excel(excel_file, dtype=str)

        invalid_count = df["Is_Invalid"].sum()

        # ✅ Toggle
        show_invalid = st.toggle(f"Show Invalid ({invalid_count})")

        display = df[df["Is_Invalid"]] if show_invalid else df

        # ✅ Highlight rows
        def highlight(row):
            return ["background-color: #ffe6e6"] * len(row) if row["Is_Invalid"] else [""] * len(row)

        st.dataframe(display.style.apply(highlight, axis=1), use_container_width=True)

        # ✅ UNIQUE PAIRS (same position)
        st.subheader("Unique Pairs")

        if st.session_state.auto_fixed and st.session_state.corrected_pairs is not None:
            st.dataframe(st.session_state.corrected_pairs, use_container_width=True)

        else:
            def highlight_pairs(row):
                return ["background-color: #ffe6e6"] * len(row) if row["Is_Invalid"] else [""] * len(row)

            st.dataframe(
                unique_pairs.style.apply(highlight_pairs, axis=1),
                use_container_width=True
            )

        # ✅ AUTO FIX
        st.subheader("Auto Fix")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Apply Auto Fix"):

                corrected_df = st.session_state.original_df.copy()

                for i in range(len(df)):

                    if df.loc[i, "Reason"] == "Spelling Error":
                        sugg = df.loc[i, "Suggestion"]
                        if sugg != "No suggestion":
                           
