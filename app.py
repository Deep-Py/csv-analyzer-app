import streamlit as st
import pandas as pd
import os
import tempfile

# -------------------------------
# Page Config
# -------------------------------
st.set_page_config(page_title="CSV Analyzer", layout="wide")
st.title("📊 CSV Folder Analyzer")

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

# ✅ NEW: Folder Path Input
folder_path = st.sidebar.text_input("Enter folder path containing CSV files")

process_clicked = st.sidebar.button("▶️ Process Files")
clear_clicked = st.sidebar.button("🧹 Clear Results")

# -------------------------------
# Session State
# -------------------------------
if "results" not in st.session_state:
    st.session_state.results = []

# -------------------------------
# Helper Functions
# -------------------------------
def get_csv_files(folder):
    try:
        return [
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if f.lower().endswith(".csv")
        ]
    except Exception:
        return None


def process_csv(file_path, has_header):
    try:
        if has_header:
            df = pd.read_csv(file_path, header=0)
        else:
            df = pd.read_csv(file_path, header=None)

        if df.empty:
            raise ValueError("Empty file")

        col = df.iloc[:, 0].dropna()

        if col.empty:
            raise ValueError("No valid data in first column")

        return len(col), col.nunique(), None

    except Exception as e:
        return None, None, str(e)


def convert_csv(df):
    return df.to_csv(index=False).encode("utf-8")


def convert_excel(df):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        df.to_excel(tmp.name, index=False)
        return open(tmp.name, "rb").read()

# -------------------------------
# Clear Button (FULL RESET)
# -------------------------------
if clear_clicked:
    st.session_state.results = []
    st.success("✅ Cleared results")

# -------------------------------
# Process Files
# -------------------------------
if process_clicked:

    if not folder_path:
        st.error("❌ Please provide a folder path")
    else:
        files = get_csv_files(folder_path)

        if files is None:
            st.error("❌ Invalid folder path")
        elif len(files) == 0:
            st.error("❌ No CSV files found in folder")
        else:
            results = []

            progress = st.progress(0)
            status = st.empty()

            total_files = len(files)

            for i, file in enumerate(files):

                filename = os.path.basename(file)
                status.text(f"Processing {filename} ({i+1}/{total_files})")

                total, unique, error = process_csv(file, has_header)

                if error:
                    st.warning(f"{filename}: {error}")
                else:
                    results.append({
                        "File Name": filename,
                        "Total Count": total,
                        "Unique Count": unique
                    })

                progress.progress((i + 1) / total_files)

            st.session_state.results = results
            status.text("✅ Processing completed")

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

    # Export
    st.subheader("⬇️ Export")

    c1, c2 = st.columns(2)

    with c1:
        st.download_button(
            "Download CSV",
            data=convert_csv(df),
            file_name="results.csv"
        )

    with c2:
        st.download_button(
            "Download Excel",
            data=convert_excel(df),
            file_name="results.xlsx"
        )

else:
    st.info("👈 Enter folder path and click Process")
