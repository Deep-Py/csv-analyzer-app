import streamlit as st
import pandas as pd
import tempfile

# -------------------------------
# Page Configuration
# -------------------------------
st.set_page_config(
    page_title="CSV Analyzer",
    page_icon="📊",
    layout="wide"
)

st.title("📊 CSV Folder Analyzer")

# -------------------------------
# Session State
# -------------------------------
if "results" not in st.session_state:
    st.session_state.results = []

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# -------------------------------
# Sidebar Controls
# -------------------------------
st.sidebar.header("⚙️ Controls")

view_mode = st.sidebar.selectbox(
    "View Mode",
    ["Both", "Total Count", "Unique Count"]
)

has_header = st.sidebar.checkbox(
    "CSV files contain header row",
    value=True
)

uploaded_files = st.sidebar.file_uploader(
    "Upload CSV Files",
    type=["csv"],
    accept_multiple_files=True,
    key=f"uploader_{st.session_state.uploader_key}"
)

process_clicked = st.sidebar.button("▶️ Process Files")
clear_clicked = st.sidebar.button("🧹 Clear Results")

# -------------------------------
# Helper Functions
# -------------------------------
def process_csv(file, has_header):
    try:
        if has_header:
            df = pd.read_csv(file, header=0)
        else:
            df = pd.read_csv(file, header=None)

        if df.empty:
            raise ValueError("File is empty")

        col = df.iloc[:, 0].dropna()

        if col.empty:
            raise ValueError("First column has no valid data")

        return len(col), col.nunique(), None

    except Exception as e:
        return None, None, str(e)


def convert_csv(df):
    return df.to_csv(index=False).encode("utf-8")


def convert_excel(df):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        df.to_excel(tmp.name, index=False)
        return open(tmp.name, "rb").read()


# ✅ SUMMARY GENERATION

def generate_comment(results):

    added = []
    deleted = []

    # ✅ Categorize by filename
    for file in results:
        name = file["File Name"].upper()

        if "ADD" in name:
            added.append(file)

        elif "DELETE" in name or "REMOVE" in name:
            deleted.append(file)

    if not added and not deleted:
        return "⚠️ No files matched ADD / DELETE / REMOVE pattern."

    # ✅ Domain extraction function
    def get_domain(filename):
        name = filename.upper()

        if "EZ_ADDT_RESTR" in name:
            return "EZ_ADDT_RESTR"
        elif "EZ_TIME_RESTR" in name:
            return "EZ_TIME_RESTR"
        elif "EZ_RESTR" in name:
            return "EZ_RESTR"
        else:
            return filename.replace(".csv", "")  # fallback

    # ✅ Totals
    total_added = sum(file["Total Count"] for file in added)
    total_deleted = sum(file["Total Count"] for file in deleted)

    # ✅ Build comment
    comment = "MMT Updates Completed:\n\n"

    # ✅ Added Section
    if added:
        comment += "Added Records:\n"
        for file in added:
            domain = get_domain(file["File Name"])
            comment += f"  • {file['Total Count']} records added into {domain} domain combo.\n"
        comment += "\n"

    # ✅ Deleted Section
    if deleted:
        comment += "Deleted Records:\n"
        for file in deleted:
            domain = get_domain(file["File Name"])
            comment += f"  • {file['Total Count']} records deleted from {domain} domain combo.\n"
        comment += "\n"

    # ✅ Totals at END (your requirement)
    comment += "Summary:\n"
    comment += f"  • Total Added Records: {total_added}\n"
    comment += f"  • Total Deleted Records: {total_deleted}\n\n"

    comment += "Thanks,\nDeepesh Pawar"

    return comment

# -------------------------------
# Clear Button
# -------------------------------
if clear_clicked:
    st.session_state.results = []
    st.session_state.uploader_key += 1
    st.success("✅ Results and uploaded files cleared")

# -------------------------------
# Process Files
# -------------------------------
if process_clicked:

    if not uploaded_files:
        st.error("❌ Please upload at least one CSV file")
    else:
        results = []

        progress_bar = st.progress(0)
        status_text = st.empty()

        total_files = len(uploaded_files)

        for i, file in enumerate(uploaded_files):
            status_text.text(f"Processing {file.name} ({i+1}/{total_files})")

            total, unique, error = process_csv(file, has_header)

            if error:
                st.warning(f"{file.name}: {error}")
            else:
                results.append({
                    "File Name": file.name,
                    "Total Count": total,
                    "Unique Count": unique
                })

            progress_bar.progress((i + 1) / total_files)

        st.session_state.results = results
        status_text.text("✅ Processing completed")

# -------------------------------
# Display Results
# -------------------------------
if st.session_state.results:

    df = pd.DataFrame(st.session_state.results)

    st.subheader("📋 Results")

    if view_mode == "Total Count":
        display_df = df[["File Name", "Total Count"]]
    elif view_mode == "Unique Count":
        display_df = df[["File Name", "Unique Count"]]
    else:
        display_df = df

    st.dataframe(display_df, use_container_width=True)

    # ✅ SUMMARY OUTPUT
    st.subheader("📝 Generated Summary")

    comment_text = generate_comment(st.session_state.results)

    st.text_area(
        "Copy this summary",
        value=comment_text,
        height=300
    )

    st.download_button(
        "Download Summary (.txt)",
        data=comment_text,
        file_name="summary.txt"
    )

    # ✅ EXPORT
    st.subheader("⬇️ Export Results")

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            "Download CSV",
            data=convert_csv(df),
            file_name="results.csv"
        )

    with col2:
        st.download_button(
            "Download Excel",
            data=convert_excel(df),
            file_name="results.xlsx"
        )

else:
    st.info("👆 Upload CSV files and click 'Process Files'")
