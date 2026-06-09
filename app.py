# import streamlit as st
# import pandas as pd
# import tempfile

# # -------------------------------
# # Page Configuration
# # -------------------------------
# st.set_page_config(
#     page_title="CSV Analyzer",
#     page_icon="📊",
#     layout="wide"
# )

# st.title("📊 CSV Folder Analyzer")

# # -------------------------------
# # Session State
# # -------------------------------
# if "results" not in st.session_state:
#     st.session_state.results = []

# if "uploader_key" not in st.session_state:
#     st.session_state.uploader_key = 0

# # -------------------------------
# # Sidebar Controls
# # -------------------------------
# st.sidebar.header("⚙️ Controls")

# view_mode = st.sidebar.selectbox(
#     "View Mode",
#     ["Both", "Total Count", "Unique Count"]
# )

# has_header = st.sidebar.checkbox(
#     "CSV files contain header row",
#     value=True
# )

# uploaded_files = st.sidebar.file_uploader(
#     "Upload CSV Files",
#     type=["csv"],
#     accept_multiple_files=True,
#     key=f"uploader_{st.session_state.uploader_key}"
# )

# process_clicked = st.sidebar.button("▶️ Process Files")
# clear_clicked = st.sidebar.button("🧹 Clear Results")

# # -------------------------------
# # Helper Functions
# # -------------------------------
# def process_csv(file, has_header):
#     try:
#         if has_header:
#             df = pd.read_csv(file, header=0)
#         else:
#             df = pd.read_csv(file, header=None)

#         if df.empty:
#             raise ValueError("File is empty")

#         col = df.iloc[:, 0].dropna()

#         if col.empty:
#             raise ValueError("First column has no valid data")

#         return len(col), col.nunique(), None

#     except Exception as e:
#         return None, None, str(e)


# def convert_csv(df):
#     return df.to_csv(index=False).encode("utf-8")


# def convert_excel(df):
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
#         df.to_excel(tmp.name, index=False)
#         return open(tmp.name, "rb").read()


# # ✅ SUMMARY GENERATION
# import re
# def generate_comment(results):

#     added = []
#     deleted = []

#     for file in results:
#         name = file["File Name"].upper()

#         # ✅ Strict ADD match (not ADDT)
#         if re.search(r'(^|_)ADD($|_)', name):
#             added.append(file)

#         # ✅ DELETE or REMOVE (safe)
#         elif re.search(r'(^|_)DELETE($|_)', name) or re.search(r'(^|_)REMOVE($|_)', name):
#             deleted.append(file)

#     if not added and not deleted:
#         return "⚠️ No files matched ADD / DELETE / REMOVE pattern."

#     # ✅ Domain Extraction
#     def get_domain(filename):
#         name = filename.upper()

#         if "EZ_ADDT_RESTR" in name:
#             return "EZ_ADDT_RESTR"
#         elif "EZ_TIME_RESTR" in name:
#             return "EZ_TIME_RESTR"
#         elif "EZ_RESTR" in name:
#             return "EZ_RESTR"
#         else:
#             return filename.replace(".csv", "")

#     total_added = sum(file["Total Count"] for file in added)
#     total_deleted = sum(file["Total Count"] for file in deleted)

#     # ✅ Build formatted output
#     comment = "MMT Updates Completed:\n\n"

#     if added:
#         comment += "Added Records:\n"
#         for file in added:
#             domain = get_domain(file["File Name"])
#             comment += f"  • {file['Total Count']} records added into {domain} domain combo.\n"
#         comment += "\n"

#     if deleted:
#         comment += "Deleted Records:\n"
#         for file in deleted:
#             domain = get_domain(file["File Name"])
#             comment += f"  • {file['Total Count']} records deleted from {domain} domain combo.\n"
#         comment += "\n"

#     comment += "Summary:\n"
#     comment += f"  • Total Added Records: {total_added}\n"
#     comment += f"  • Total Deleted Records: {total_deleted}\n\n"

#     comment += "Thanks,\nDeepesh Pawar"

#     return comment
# # -------------------------------
# # Clear Button
# # -------------------------------
# if clear_clicked:
#     st.session_state.results = []
#     st.session_state.uploader_key += 1
#     st.success("✅ Results and uploaded files cleared")

# # -------------------------------
# # Process Files
# # -------------------------------
# if process_clicked:

#     if not uploaded_files:
#         st.error("❌ Please upload at least one CSV file")
#     else:
#         results = []

#         progress_bar = st.progress(0)
#         status_text = st.empty()

#         total_files = len(uploaded_files)

#         for i, file in enumerate(uploaded_files):
#             status_text.text(f"Processing {file.name} ({i+1}/{total_files})")

#             total, unique, error = process_csv(file, has_header)

#             if error:
#                 st.warning(f"{file.name}: {error}")
#             else:
#                 results.append({
#                     "File Name": file.name,
#                     "Total Count": total,
#                     "Unique Count": unique
#                 })

#             progress_bar.progress((i + 1) / total_files)

#         st.session_state.results = results
#         status_text.text("✅ Processing completed")

# # -------------------------------
# # Display Results
# # -------------------------------
# if st.session_state.results:

#     df = pd.DataFrame(st.session_state.results)

#     st.subheader("📋 Results")

#     if view_mode == "Total Count":
#         display_df = df[["File Name", "Total Count"]]
#     elif view_mode == "Unique Count":
#         display_df = df[["File Name", "Unique Count"]]
#     else:
#         display_df = df

#     st.dataframe(display_df, use_container_width=True)

#     # ✅ SUMMARY OUTPUT
#     st.subheader("📝 Generated Summary")

#     comment_text = generate_comment(st.session_state.results)

#     st.text_area(
#         "Copy this summary",
#         value=comment_text,
#         height=300
#     )

#     st.download_button(
#         "Download Summary (.txt)",
#         data=comment_text,
#         file_name="summary.txt"
#     )

#     # ✅ EXPORT
#     st.subheader("⬇️ Export Results")

#     col1, col2 = st.columns(2)

#     with col1:
#         st.download_button(
#             "Download CSV",
#             data=convert_csv(df),
#             file_name="results.csv"
#         )

#     with col2:
#         st.download_button(
#             "Download Excel",
#             data=convert_excel(df),
#             file_name="results.xlsx"
#         )

# else:
#     st.info("👆 Upload CSV files and click 'Process Files'")

import streamlit as st
import pandas as pd
import tempfile
import re

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
    """✅ Fix numeric + string mismatch"""
    return str(x).strip().upper().replace(".0", "")


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


# ✅ SUMMARY
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


# ✅ VALIDATION (FIXED)
def validate_pairs_from_github(excel_file):
    try:
        ref_df = pd.read_csv(REFERENCE_FILE_URL)

        # ✅ Clean reference properly
        value_ref = ref_df.iloc[:, 1].apply(clean_value)
        pub_ref = ref_df.iloc[:, 0].apply(clean_value)

        ref_pairs = set(zip(value_ref, pub_ref))

        df = pd.read_excel(excel_file)

        val = df.iloc[:, 3].apply(clean_value)
        pub = df.iloc[:, 4].apply(clean_value)

        df["Value"] = val
        df["Published Value"] = pub
        df["Pair"] = list(zip(val, pub))

        df["Status"] = df["Pair"].apply(
            lambda x: "✅ Valid" if x in ref_pairs else "❌ Invalid"
        )

        unique_pairs = df[["Value", "Published Value"]].drop_duplicates()

        valid_count = (df["Status"] == "✅ Valid").sum()
        invalid_count = (df["Status"] == "❌ Invalid").sum()

        return df, unique_pairs, valid_count, invalid_count, None

    except Exception as e:
        return None, None, None, None, str(e)

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
# DISPLAY CSV
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
# DISPLAY VALIDATION
# -------------------------------
if validate_clicked:

    if not excel_file:
        st.error("Upload Excel file")
    else:
        df_val, unique_pairs, valid, invalid, err = validate_pairs_from_github(excel_file)

        if err:
            st.error(err)
        else:
            st.subheader("✅ Validation Results")

            def highlight(row):
                return ['background-color: #ffcccc' if row.Status == "❌ Invalid" else '' for _ in row]

            st.dataframe(df_val.style.apply(highlight, axis=1), use_container_width=True)

            st.markdown(f"""
            **Summary**
            - ✅ Valid: {valid}
            - ❌ Invalid: {invalid}
            """)

            st.subheader("🔹 Unique Pairs")
            st.dataframe(unique_pairs, use_container_width=True)

