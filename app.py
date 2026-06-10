import streamlit as st
import pandas as pd
import tempfile
import re
from difflib import get_close_matches
from io import BytesIO

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

if "corrected_file" not in st.session_state:
    st.session_state.corrected_file = None

# ===============================
# CACHE
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
        match = get_close_matches(value, reference_list, n=1, cutoff=0.5)
        if match:
            return match[0]
        for ref_val in reference_list:
            if value in ref_val:
                return ref_val
        return "No suggestion"

    ref["Vehicle"] = ref.iloc[:, 0].apply(clean_value)
    ref["Vehicle_ID"] = ref.iloc[:, 1].apply(clean_value)

    vehicle_map = {}
    for v, vid in zip(ref["Vehicle"], ref["Vehicle_ID"]):
        vehicle_map.setdefault(v, set()).add(vid)

    vehicles = list(vehicle_map.keys())

    df = pd.read_excel(BytesIO(file_bytes), dtype=str)

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

    total_added = sum(f["Total"] for f in added) if added else 0
    total_deleted = sum(f["Total"] for f in deleted) if deleted else 0

    comment = "MMT Updates Completed:\n\n"

    if added:
        comment += "Added Records:\n"
        for f in added:
            comment += f"  • {f['Total']} records added into {get_domain(f['File Name'])} domain combo.\n"
        comment += "\n"

    if deleted:
        comment += "Deleted Records:\n"
        for f in deleted:
            comment += f"  • {f['Total']} records deleted from {get_domain(f['File Name'])} domain combo.\n"
        comment += "\n"

    comment += "Summary:\n"
    comment += f"  • Total Added Records: {total_added}\n"
    comment += f"  • Total Deleted Records: {total_deleted}\n\n"

    comment += "Thanks,\nDeepesh Pawar"

    return comment


# ===============================
# UI TABS
# ===============================
tab1, tab2 = st.tabs(["CSV Analyzer", "Excel Validation"])

# ===============================
# CSV TAB
# ===============================


with tab1:

    if "csv_uploader_key" not in st.session_state:
        st.session_state.csv_uploader_key = 0

    st.subheader("📊 CSV Analyzer")

    col1, col2, col3 = st.columns(3)

    # ✅ Header option
    with col1:
        has_header = st.checkbox("CSV has header row", value=True)

    # ✅ View dropdown
    with col2:
        view_mode = st.selectbox(
            "View Mode",
            ["Both", "Total Count", "Unique Count"]
        )

    # ✅ Clear Button
    with col3:
        if st.button("Clear Files"):
            st.session_state.csv_uploader_key += 1
            st.rerun()

    # ✅ File uploader
    files = st.file_uploader(
        "Upload CSV files",
        type=["csv"],
        accept_multiple_files=True,
        key=f"csv_upload_{st.session_state.csv_uploader_key}"
    )

    if files:

        results = []

        for f in files:

            try:
                df = pd.read_csv(f, header=0 if has_header else None)

                if df.empty:
                    continue

            except Exception as e:
                st.error(f"{f.name}: {e}")
                continue

            # ✅ First column only
            col = df.iloc[:, 0]

            total = col.dropna().shape[0]
            unique = col.nunique()
            missing = col.isna().sum()

            results.append({
                "File Name": f.name,
                "Total": total,
                "Unique": unique,
                "Missing": missing
            })

        # ✅ Create summary dataframe
        df_res = pd.DataFrame(results)

        st.subheader("📋 Summary Table")

        if view_mode == "Total Count":
            display_df = df_res[["File Name", "Total"]]

        elif view_mode == "Unique Count":
            display_df = df_res[["File Name", "Unique"]]

        else:
            display_df = df_res

        st.dataframe(display_df, use_container_width=True)

        # ✅ Download summary
        st.download_button(
            "Download Summary CSV",
            display_df.to_csv(index=False),
            "summary.csv"
        )

        # ✅ Generated comment
        st.subheader("📝 Generated Summary")

        st.text_area(
            "",
            generate_summary(results),
            height=250
        )

# ===============================
# VALIDATION TAB
# ===============================
with tab2:

    excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])

    if excel_file:

        file_bytes = excel_file.getvalue()

        df, unique_pairs, vehicle_map = validate_pairs(file_bytes)

        # ✅ Cache original once
        if st.session_state.original_df is None:
            st.session_state.original_df = pd.read_excel(BytesIO(file_bytes), dtype=str)

        invalid_count = df["Is_Invalid"].sum()

        show_invalid = st.toggle(f"Show Invalid ({invalid_count})")

        display = df[df["Is_Invalid"]] if show_invalid else df

        # ✅ Highlight
        def highlight(row):
            return ["background-color: #ffe6e6"] * len(row) if row["Is_Invalid"] else [""] * len(row)

        st.dataframe(display.style.apply(highlight, axis=1), use_container_width=True)

        # ===============================
        # UNIQUE PAIRS
        # ===============================
        st.subheader("Unique Pairs")

        if st.session_state.auto_fixed and st.session_state.corrected_pairs is not None:
            st.dataframe(st.session_state.corrected_pairs, use_container_width=True)
        else:
            def highlight_pairs(row):
                return ["background-color: #ffe6e6"] * len(row) if row["Is_Invalid"] else [""] * len(row)

            st.dataframe(unique_pairs.style.apply(highlight_pairs, axis=1), use_container_width=True)

        # ===============================
        # AUTO FIX
        # ===============================
        st.subheader("Auto Fix")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Apply Auto Fix"):

                corrected_df = st.session_state.original_df.copy()

                for i in range(len(df)):

                    if df.loc[i, "Reason"] == "Spelling Error":
                        sugg = df.loc[i, "Suggestion"]
                        if sugg != "No suggestion":
                            corrected_df.iloc[i, 3] = sugg

                    elif "Mapping Error" in df.loc[i, "Reason"]:
                        val = df.loc[i, "Value"]
                        if val in vehicle_map:
                            corrected_df.iloc[i, 4] = list(vehicle_map[val])[0]

                corrected_pairs = pd.DataFrame({
                    "Value": corrected_df.iloc[:, 3],
                    "Published Value": corrected_df.iloc[:, 4]
                }).drop_duplicates().reset_index(drop=True)

                st.session_state.auto_fixed = True
                st.session_state.corrected_pairs = corrected_pairs
                st.session_state.corrected_file = corrected_df

                st.success("✅ Auto Fix Applied")
                st.rerun()

        # ===============================
        # RESET
        # ===============================
        with col2:
            if st.session_state.auto_fixed:
                if st.button("Reset / Undo Fix"):
                    st.session_state.auto_fixed = False
                    st.session_state.corrected_pairs = None
                    st.session_state.corrected_file = None
                    st.rerun()

        # ===============================
        # DOWNLOAD + INFO
        # ===============================
        if st.session_state.auto_fixed and st.session_state.corrected_file is not None:

            filename = excel_file.name.replace(".xlsx", "_corrected.xlsx")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                st.session_state.corrected_file.to_excel(tmp.name, index=False)
                clean_file = open(tmp.name, "rb").read()

            # ✅ Metrics
            row_count = len(st.session_state.corrected_file)
            file_size_kb = round(len(clean_file) / 1024, 2)

            st.success("✅ Corrected file ready for download")

            col1, col2 = st.columns(2)
            col1.metric("Rows", row_count)
            col2.metric("File Size (KB)", file_size_kb)

            st.download_button(
                "Download Corrected File",
                clean_file,
                filename
            )

        # ===============================
        # DOWNLOAD ERRORS
        # ===============================
        error_df = df[df["Is_Invalid"]]

        st.download_button(
            "Download Errors",
            error_df.to_csv(index=False),
            "errors.csv"
        )
