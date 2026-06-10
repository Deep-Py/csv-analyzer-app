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


def process_csv(file, has_header):
    try:
        df = pd.read_csv(file, header=0 if has_header else None)
        col = df.iloc[:, 0].dropna()
        return len(col), col.nunique(), None
    except Exception as e:
        return None, None, str(e)


def convert_csv(df):
    return df.to_csv(index=False).encode("utf-8")


def convert_excel(df):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        df.to_excel(tmp.name, index=False)
        return open(tmp.name, "rb").read()


# ✅ SUMMARY FUNCTION
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


# ✅ FINAL VALIDATION FUNCTION (CORRECT LOGIC)
def validate_pairs_from_github(excel_file):

    try:
        ref_df = pd.read_csv(REFERENCE_FILE_URL, dtype=str)

        def clean_value(x):
            if pd.isna(x):
                return ""
            x = str(x).strip().upper().replace("\xa0", "")
            if x.endswith(".0"):
                x = x[:-2]
            if x.isdigit():
                x = str(int(x))
            return x

        # ✅ Reference mapping
        ref_df["Vehicle"] = ref_df.iloc[:, 0].apply(clean_value)
        ref_df["Vehicle_ID"] = ref_df.iloc[:, 1].apply(clean_value)

        vehicle_to_id_map = {}
        for v, vid in zip(ref_df["Vehicle"], ref_df["Vehicle_ID"]):
            if v not in vehicle_to_id_map:
                vehicle_to_id_map[v] = set()
            vehicle_to_id_map[v].add(vid)

        all_vehicles = list(vehicle_to_id_map.keys())

        # ✅ Excel
        df = pd.read_excel(excel_file, dtype=str)

        df["Value"] = df.iloc[:, 3].apply(clean_value)
        df["Published Value"] = df.iloc[:, 4].apply(clean_value)

        status_list = []
        reason_list = []
        suggestion_list = []

        for val, pub in zip(df["Value"], df["Published Value"]):

            if val not in vehicle_to_id_map:
                # ✅ Suggest closest match
                suggestion = get_close_matches(val, all_vehicles, n=1)
                suggestion_text = suggestion[0] if suggestion else "No suggestion"

                status_list.append("❌ Invalid")
                reason_list.append("Spelling Error")
                suggestion_list.append(suggestion_text)

            elif pub not in vehicle_to_id_map[val]:
                expected = ", ".join(vehicle_to_id_map[val])
                status_list.append("❌ Invalid")
                reason_list.append(f"Mapping Mismatch (Expected ID: {expected})")
                suggestion_list.append(val)

            else:
                status_list.append("✅ Valid")
                reason_list.append("Correct Mapping")
                suggestion_list.append("")

        df["Status"] = status_list
        df["Reason"] = reason_list
        df["Suggestion"] = suggestion_list

        unique_pairs = df[["Value", "Published Value"]].drop_duplicates()

        valid_count = (df["Status"] == "✅ Valid").sum()
        invalid_count = (df["Status"] == "❌ Invalid").sum()

        # Error breakdown
        spelling_errors = (df["Reason"] == "Spelling Error").sum()
        mapping_errors = df["Reason"].str.contains("Mapping Mismatch").sum()

        return df, unique_pairs, valid_count, invalid_count, spelling_errors, mapping_errors, None

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

    if not uploaded_files:
        st.error("Upload CSV files")
    else:
        results = []
        progress = st.progress(0)
        total = len(uploaded_files)

        for i, file in enumerate(uploaded_files):

            total_c, unique_c, err = process_csv(file, has_header)

            if not err:
                results.append({
                    "File Name": file.name,
                    "Total Count": total_c,
                    "Unique Count": unique_c
                })
            else:
                st.warning(f"{file.name}: {err}")

            progress.progress((i + 1) / total)

        st.session_state.results = results

# -------------------------------
# DISPLAY CSV RESULTS
# -------------------------------
if st.session_state.results:

    df = pd.DataFrame(st.session_state.results)

    st.subheader("📋 CSV Results")

    if view_mode == "Total Count":
        df = df[["File Name", "Total Count"]]
    elif view_mode == "Unique Count":
        df = df[["File Name", "Unique Count"]]

    st.dataframe(df, use_container_width=True)

    st.subheader("📝 Summary")

    st.text_area("Copy Summary", generate_comment(st.session_state.results), height=300)


# -------------------------------
# VALIDATION OUTPUT
# -------------------------------
if validate_clicked:

    if not excel_file:
        st.error("Upload Excel file")
    else:
        df_val, unique_pairs, valid, invalid, spelling_err, mapping_err, err = validate_pairs_from_github(excel_file)

        if err:
            st.error(err)
        else:
            st.subheader("✅ Validation Results")

            # ✅ Toggle
            show_invalid_only = st.checkbox("Show Only Invalid Records")

            display_df = df_val[df_val["Status"] == "❌ Invalid"] if show_invalid_only else df_val

            # ✅ Highlight
            def highlight(row):
                return ['background-color: #ffcccc' if row.Status == "❌ Invalid" else '' for _ in row]

            st.dataframe(display_df.style.apply(highlight, axis=1), use_container_width=True)

            # ✅ Summary
            st.subheader("📊 Summary")

            col1, col2 = st.columns(2)

            with col1:
                st.metric("✅ Valid", valid)
                st.metric("❌ Invalid", invalid)

            with col2:
                st.metric("Spelling Errors", spelling_err)
                st.metric("Mapping Errors", mapping_err)

            # ✅ Charts
            chart_data = pd.DataFrame({
                "Type": ["Valid", "Invalid"],
                "Count": [valid, invalid]
            })

            st.bar_chart(chart_data.set_index("Type"))

            error_data = pd.DataFrame({
                "Type": ["Spelling", "Mapping"],
                "Count": [spelling_err, mapping_err]
            })

            st.bar_chart(error_data.set_index("Type"))

            # ✅ Export only invalid
            invalid_df = df_val[df_val["Status"] == "❌ Invalid"]

            st.subheader("⬇️ Export Errors")

            c1, c2 = st.columns(2)

            with c1:
                st.download_button(
                    "Download Errors CSV",
                    invalid_df.to_csv(index=False).encode("utf-8"),
                    "errors.csv"
                )

            with c2:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    invalid_df.to_excel(tmp.name, index=False)
                    data = open(tmp.name, "rb").read()

                st.download_button(
                    "Download Errors Excel",
                    data,
                    "errors.xlsx"
                )

            # ✅ Unique pairs
            st.subheader("🔹 Unique Pairs")
            st.dataframe(unique_pairs, use_container_width=True)

