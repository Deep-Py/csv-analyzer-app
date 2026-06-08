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
# Sidebar Controls
# -------------------------------
st.sidebar.header("⚙️ Controls")

view_mode = st.sidebar.selectbox(
    "View Mode",
    ["Both", "Total Count", "Unique Count"]
)

# ✅ NEW: Header Option
has_header = st.sidebar.checkbox("CSV has header row", value=False)

uploaded_files = st.sidebar.file_uploader(
    "Upload CSV Files",
    type=["csv"],
    accept_multiple_files=True
)

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
def process_csv(file, has_header):
    try:
        # ✅ Use checkbox value
        if has_header:
            df = pd.read_csv(file)
        else:
            df = pd.read_csv(file, header=None)

        if df.empty:
            raise ValueError("File is empty")

        first_col = df.iloc[:, 0].dropna()

        if first_col.empty:
            raise ValueError("First column has no valid data")

        total_count = len(first_col)
        unique_count = first_col.nunique()

        return total_count, unique_count, None

    except Exception as e:
        return None, None, str(e)


def convert_to_csv(df):
    return df.to_csv(index=False).encode("Great idea—this makes your app **much more flexible and accurate** ✅  

Below is the **complete updated `app.py`** with a **“Header Row” checkbox** added.

---

# ✅ ✅ What’s Added
- ✅ Checkbox: **"CSV files contain header row"**
- ✅ Logic adjusts automatically:
  - Checked → `header=0`
  - Unchecked → `header=None`
- ✅ Works for mixed use cases

---

# 📄 ✅ Updated `app.py` (FULL CODE)

```python
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

# -------------------------------
# Header
# -------------------------------
st.title("📊 CSV Folder Analyzer (Web App)")
st.markdown("Upload multiple CSV files and analyze their first column.")

# -------------------------------
# Sidebar Controls
# -------------------------------
st.sidebar.header("⚙️ Controls")

view_mode = st.sidebar.selectbox(
    "View Mode",
    ["Both", "Total Count", "Unique Count"]
)

# ✅ NEW: Header Checkbox
has_header = st.sidebar.checkbox(
    "CSV files contain header row",
    value=True
)

uploaded_files = st.sidebar.file_uploader(
    "Upload CSV Files",
    type=["csv"],
    accept_multiple_files=True
)

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
def process_csv(file, has_header):
    try:
        if has_header:
            df = pd.read_csv(file, header=0)
        else:
            df = pd.read_csv(file, header=None)

        if df.empty:
            raise ValueError("File is empty")

        first_col = df.iloc[:, 0].dropna()

        if first_col.empty:
            raise ValueError("First column has no valid data")

        total_count = len(first_col)
        unique_count = first_col.nunique()

        return total_count, unique_count, None

    except Exception as e:
        return None, None, str(e)


def convert_to_csv(df):
    return df.to_csv(index=False).encode("utf-8")


def convert_to_excel(df):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        df.to_excel(tmp.name, index=False)
        data = open(tmp.name, "rb").read()
    return data


# -------------------------------
# Process Files
# -------------------------------
if process_clicked:

    if not uploaded_files:
        st.error("❌ Please upload at least one CSV file.")
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
        status_text.text("✅ Processing completed successfully!")

# -------------------------------
# Clear Results
# -------------------------------
if clear_clicked:
    st.session_state.results = []
    st.success("✅ Results cleared")

# -------------------------------
# Display Results
# -------------------------------
if st.session_state.results:

    df = pd.DataFrame(st.session_state.results)

    st.subheader("📋 Results")

    # View filtering
    if view_mode == "Total Count":
        display_df = df[["File Name", "Total Count"]]
    elif view_mode == "Unique Count":
        display_df = df[["File Name", "Unique Count"]]
    else:
        display_df = df

    st.dataframe(display_df, use_container_width=True)

    # ---------------------------
    # Export Section
    # ---------------------------
    st.subheader("⬇️ Export Results")

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label="Download as CSV",
            data=convert_to_csv(df),
            file_name="csv_analysis_results.csv",
            mime="text/csv"
        )

    with col2:
        st.download_button(
            label="Download as Excel",
            data=convert_to_excel(df),
            file_name="csv_analysis_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("👆 Upload CSV files and click 'Process Files' to start.")
