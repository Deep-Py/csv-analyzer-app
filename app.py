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
        if value in ref:
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

    total_added = sum(x["Total"] for x in added)
    total_deleted = sum(x["Total"] for x in deleted)

    text = "MMT Updates Completed:\n\n"

    if added:
        text += "Added Records:\n"
        for f in added:
            text += f"  • {f['Total']} records added from {f['File Name']}\n"
        text += "\n"

    if deleted:
        text += "Deleted Records:\n"
        for f in deleted:
            text += f"  • {f['Total']} records deleted from {f['File Name']}\n"
        text += "\n"

    text += f"Summary:\n  • Added: {total_added}\n  • Deleted: {total_deleted}"

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
# TABS
# ===============================
tab1, tab2 = st.tabs(["CSV Analyzer", "Excel Validation"])

# ===============================
# CSV TAB
# ===============================
with tab1:

    files = st.file_uploader("Upload CSV Files", type=["csv"], accept_multiple_files=True)

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

        st.dataframe(df)
        st.text_area("Summary", generate_summary(results), height=200)

# ===============================
# VALIDATION TAB
# ===============================
with tab2:

    excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])

    if excel_file:

        df, unique_pairs, vehicle_map = validate_pairs(excel_file)

        invalid_count = df["Is_Invalid"].sum()

        # ✅ TOGGLE
        show_invalid = st.toggle(f"Show Invalid ({invalid_count})")

        display = df.copy()

        if show_invalid:
            display = display[display["Is_Invalid"]]

        st.subheader("Validation Results")

        # ✅ Highlight invalid rows
        def highlight(row):
            return ["background-color: #ffe6e6"] * len(row) if row["Is_Invalid"] else [""] * len(row)

        st.dataframe(display.style.apply(highlight, axis=1), use_container_width=True)

        # ✅ UNIQUE PAIRS SECTION (SAME POSITION)
        st.subheader("Unique Pairs")

        if st.session_state.auto_fixed and st.session_state.corrected_pairs is not None:
            st.dataframe(st.session_state.corrected_pairs)

        else:
            def highlight_pairs(row):
                return ["background-color: #ffe6e6"] * len(row) if row["Is_Invalid"] else [""] * len(row)

            st.dataframe(
                unique_pairs.style.apply(highlight_pairs, axis=1),
                use_container_width=True
            )

        # ✅ AUTO FIX
        st.subheader("Auto Fix")

        if st.button("Apply Auto Fix"):

            original_df = pd.read_excel(excel_file, dtype=str)
            corrected_df = original_df.copy()

            for i in range(len(df)):

                if df.loc[i, "Reason"] == "Spelling Error":
                    suggestion = df.loc[i, "Suggestion"]
                    if suggestion != "No suggestion":
                        corrected_df.iloc[i, 3] = suggestion

                elif "Mapping Error" in df.loc[i, "Reason"]:
                    val = df.loc[i, "Value"]
                    if val in vehicle_map:
                        corrected_df.iloc[i, 4] = list(vehicle_map[val])[0]

            corrected_pairs = pd.DataFrame({
                "Value": corrected_df.iloc[:, 3].apply(clean_value),
                "Published Value": corrected_df.iloc[:, 4].apply(clean_value)
            }).drop_duplicates()

            st.session_state.auto_fixed = True
            st.session_state.corrected_pairs = corrected_pairs

            # ✅ FILE NAME SAME
            filename = excel_file.name.replace(".xlsx", "_corrected.xlsx")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                corrected_df.to_excel(tmp.name, index=False)
                clean_file = open(tmp.name, "rb").read()

            st.download_button("Download Corrected File", clean_file, filename)

        # ✅ RESET BUTTON
        if st.session_state.auto_fixed:
            if st.button("Reset / Undo Fix"):
                st.session_state.auto_fixed = False
                st.session_state.corrected_pairs = None
                st.success("Reset successful")

        # ✅ DOWNLOAD ERRORS
        error_df = df[df["Is_Invalid"]]

        st.download_button(
            "Download Errors",
            error_df.to_csv(index=False),
            "errors.csv"
        )

