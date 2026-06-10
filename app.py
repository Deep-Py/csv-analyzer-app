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
# SESSION STATE
# -------------------------------
if "results" not in st.session_state:
    st.session_state.results = []

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# -------------------------------
# SIDEBAR
# -------------------------------
st.sidebar.header("⚙️ CSV Analyzer")

view_mode = st.sidebar.selectbox(
    "View Mode",
    ["Both", "Total Count", "Unique Count"]
)

has_header = st.sidebar.checkbox("CSV has header row", True)

uploaded_files = st.sidebar.file_uploader(
    "Upload CSV Files",
    type=["csv"],
    accept_multiple_files=True,
    key=f"csv_{st.session_state.uploader_key}"
)

process_clicked = st.sidebar.button("▶️ Process CSV Files")
clear_clicked = st.sidebar.button("🧹 Clear Results")

# -------------------------------
# VALIDATION
# -------------------------------
st.sidebar.markdown("---")
st.sidebar.header("🔍 Excel Validation")

excel_file = st.sidebar.file_uploader(
    "Upload Excel File",
    type=["xlsx"],
    key="excel_file"
)

validate_clicked = st.sidebar.button("✅ Validate Pairs")

# -------------------------------
# HELPERS
# -------------------------------
def clean_value(x):
    if pd.isna(x):
        return ""

    x = str(x)
    x = (
        x.replace("\xa0", "")
         .replace("\u2007", "")
         .replace("\u202f", "")
         .strip()
         .upper()
    )

    if x.endswith(".0"):
        x = x[:-2]

    if x.isdigit():
        x = str(int(x))

    return x


def get_suggestion(value, reference_list):
    # Fuzzy match
    matches = get_close_matches(value, reference_list, n=1, cutoff=0.5)
    if matches:
        return matches[0]

    # Partial match
    for ref in reference_list:
        if value in ref or ref.startswith(value):
            return ref

    return "No suggestion"


def process_csv(file, has_header):
    try:
        df = pd.read_csv(file, header=0 if has_header else None)
        col = df.iloc[:, 0].dropna()
        return len(col), col.nunique(), None
    except Exception as e:
        return None, None, str(e)


# -------------------------------
# SUMMARY FUNCTION
# -------------------------------
def generate_comment(results):

    added, deleted = [], []

    for f in results:
        name = f["File Name"].upper()

        if re.search(r'(^|_)ADD($|_)', name):
            added.append(f)
        elif re.search(r'(^|_)DELETE($|_)', name) or re.search(r'(^|_)REMOVE($|_)', name):
            deleted.append(f)

    def get_domain(filename):
        name = filename.upper()
        if "EZ_ADDT_RESTR" in name:
            return "EZ_ADDT_RESTR"
        elif "EZ_TIME_RESTR" in name:
            return "EZ_TIME_RESTR"
        elif "EZ_RESTR" in name:
            return "EZ_RESTR"
        return filename.replace(".csv", "")

    total_added = sum(f["Total Count"] for f in added)
    total_deleted = sum(f["Total Count"] for f in deleted)

    comment = "MMT Updates Completed:\n\n"

    if added:
        comment += "Added Records:\n"
        for f in added:
            comment += f"  • {f['Total Count']} records added into {get_domain(f['File Name'])} domain combo.\n"
        comment += "\n"

    if deleted:
        comment += "Deleted Records:\n"
        for f in deleted:
            comment += f"  • {f['Total Count']} records deleted from {get_domain(f['File Name'])} domain combo.\n"
        comment += "\n"

    comment += "Summary:\n"
    comment += f"  • Total Added Records: {total_added}\n"
    comment += f"  • Total Deleted Records: {total_deleted}\n\n"

    comment += "Thanks,\nDeepesh Pawar"
    return comment


# -------------------------------
# VALIDATION FUNCTION
# -------------------------------
def validate_pairs_from_github(excel_file):

    try:
        ref_df = pd.read_csv(REFERENCE_FILE_URL, dtype=str)

        # ✅ Correct mapping
        ref_df["Vehicle"] = ref_df.iloc[:, 0].apply(clean_value)
        ref_df["Vehicle_ID"] = ref_df.iloc[:, 1].apply(clean_value)

        vehicle_to_id_map = {}
        for v, vid in zip(ref_df["Vehicle"], ref_df["Vehicle_ID"]):
            if v not in vehicle_to_id_map:
                vehicle_to_id_map[v] = set()
            vehicle_to_id_map[v].add(vid)

        all_vehicles = list(vehicle_to_id_map.keys())

        df = pd.read_excel(excel_file, dtype=str)

        df["Value"] = df.iloc[:, 3].apply(clean_value)
        df["Published Value"] = df.iloc[:, 4].apply(clean_value)

        status, reason, suggestion = [], [], []

        for val, pub in zip(df["Value"], df["Published Value"]):

            if val not in vehicle_to_id_map:
                status.append("❌ Invalid")
                reason.append("Spelling Error")
                suggestion.append(get_suggestion(val, all_vehicles))

            elif pub not in vehicle_to_id_map[val]:
                expected = ", ".join(vehicle_to_id_map[val])
                status.append("❌ Invalid")
                reason.append(f"Mapping Mismatch (Expected ID: {expected})")
                suggestion.append(val)

            else:
                status.append("✅ Valid")
                reason.append("Correct Mapping")
                suggestion.append("")

        df["Status"] = status
        df["Reason"] = reason
        df["Suggestion"] = suggestion

        unique_pairs = df[["Value", "Published Value"]].drop_duplicates()

        valid_count = (df["Status"] == "✅ Valid").sum()
        invalid_count = (df["Status"] == "❌ Invalid").sum()

        spelling_err = (df["Reason"] == "Spelling Error").sum()
        mapping_err = df["Reason"].str.contains("Mapping Mismatch").sum()

        return df, unique_pairs, valid_count, invalid_count, spelling_err, mapping_err, None

    except Exception as e:
        return None, None, None, None, None, None, str(e)


# -------------------------------
# CLEAR
# -------------------------------
if clear_clicked:
    st.session_state.results = []
    st.session_state.uploader_key += 1
    st.success("✅ Reset complete")

# -------------------------------
# PROCESS CSV
# -------------------------------
if process_clicked:
    if uploaded_files:
        results = []
        for f in uploaded_files:
            total, unique, err = process_csv(f, has_header)
            if not err:
                results.append({"File Name": f.name, "Total Count": total, "Unique Count": unique})
        st.session_state.results = results

# -------------------------------
# DISPLAY CSV RESULTS
# -------------------------------
if st.session_state.results:
    df = pd.DataFrame(st.session_state.results)
    st.dataframe(df, use_container_width=True)
    st.text_area("Summary", generate_comment(st.session_state.results), height=250)

# -------------------------------
# VALIDATION OUTPUT
# -------------------------------
if validate_clicked and excel_file:

    df_val, unique_pairs, valid, invalid, spelling_err, mapping_err, err = validate_pairs_from_github(excel_file)

    if err:
        st.error(err)
    else:
        st.subheader("✅ Validation Results")

        show_invalid_only = st.checkbox("Show Only Invalid Records")

        if show_invalid_only:
            st.dataframe(df_val[df_val["Status"] == "❌ Invalid"], use_container_width=True)
        else:
            st.dataframe(df_val, use_container_width=True)

        st.subheader("📊 Summary")
        st.write(f"✅ Valid: {valid}")
        st.write(f"❌ Invalid: {invalid}")
        st.write(f"Spelling Errors: {spelling_err}")
        st.write(f"Mapping Errors: {mapping_err}")

        # Charts
        st.bar_chart({"Valid": valid, "Invalid": invalid})
        st.bar_chart({"Spelling": spelling_err, "Mapping": mapping_err})

        # Export errors
        error_df = df_val[df_val["Status"] == "❌ Invalid"]

        st.download_button(
            "Download Errors CSV",
            error_df.to_csv(index=False).encode("utf-8"),
            "errors.csv"
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            error_df.to_excel(tmp.name, index=False)
            data = open(tmp.name, "rb").read()

        st.download_button("Download Errors Excel", data, "errors.xlsx")

        st.subheader("🔹 Unique Pairs")
        st.dataframe(unique_pairs)


