import streamlit as st
import pandas as pd
import tempfile
from difflib import get_close_matches

# -------------------------------
# CONFIG
# -------------------------------
REFERENCE_FILE_URL = "https://raw.githubusercontent.com/Deep-Py/csv-analyzer-app/main/reference.csv"


st.set_page_config(page_title="CSV Audit Assistant", layout="wide")

# -------------------------------
# UI STYLING (Website Look)
# -------------------------------
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.main {
    background-color: #f5f7fb;
}

h1 {
    text-align: center;
    color: #1f3c88;
    font-weight: 700;
}

.card {
    background-color: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

st.title("CSV Audit Assistant")

# -------------------------------
# HELPERS
# -------------------------------
def clean_value(x):
    if pd.isna(x):
        return ""
    x = str(x).strip().upper().replace("\xa0", "")
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

# -------------------------------
# VALIDATION LOGIC
# -------------------------------
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

        elif pub not in vehicle_map[val]:
            expected = ", ".join(vehicle_map[val])
            status.append("INVALID")
            reason.append(f"Mapping Error (Expected ID: {expected})")
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

    # Auto-fix (spelling only)
    fixed = df.copy()
    for i in fixed.index:
        if fixed.loc[i, "Reason"] == "Spelling Error":
            sugg = fixed.loc[i, "Suggestion"]
            if sugg != "No suggestion":
                fixed.loc[i, "Value"] = sugg

    # Metrics
    valid = (df["Status"] == "VALID").sum()
    invalid = (df["Status"] == "INVALID").sum()
    spelling = (df["Reason"] == "Spelling Error").sum()
    mapping = df["Reason"].str.contains("Mapping Error").sum()

    unique_pairs = df[["Value", "Published Value"]].drop_duplicates()

    return df, fixed, unique_pairs, valid, invalid, spelling, mapping

# -------------------------------
# UI INPUT
# -------------------------------
st.markdown('<div class="card">', unsafe_allow_html=True)

col1, col2 = st.columns([3,1])

with col1:
    excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])

with col2:
    validate = st.button("Validate")

st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------
# PROCESS
# -------------------------------
if validate and excel_file:

    df, fixed_df, unique_pairs, valid, invalid, spelling, mapping = validate_pairs(excel_file)

    # ✅ FILTER CARD
    st.markdown('<div class="card">', unsafe_allow_html=True)

    show_invalid = st.toggle(f"Show Invalid Records ({invalid})")

    filter_option = st.selectbox(
        "Filter",
        ["All Records", "Spelling Errors", "Mapping Errors"]
    )

    display = df.copy()

    if show_invalid:
        display = display[display["Is_Invalid"]]

    if filter_option == "Spelling Errors":
        display = display[display["Reason"] == "Spelling Error"]

    elif filter_option == "Mapping Errors":
        display = display[display["Reason"].str.contains("Mapping Error")]

    st.markdown('</div>', unsafe_allow_html=True)

    # ✅ TABLE CARD
    st.markdown('<div class="card">', unsafe_allow_html=True)

    def highlight(row):
        return ["background-color: #ffe6e6"] * len(row) if row["Is_Invalid"] else [""] * len(row)

    if display.empty:
        st.warning("No records found")
    else:
        st.dataframe(display.style.apply(highlight, axis=1), use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ✅ SUMMARY CARD
    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.subheader("Summary")

    c1, c2 = st.columns(2)

    with c1:
        st.metric("Valid", valid)
        st.metric("Invalid", invalid)

    with c2:
        st.metric("Spelling Errors", spelling)
        st.metric("Mapping Errors", mapping)

    st.markdown('</div>', unsafe_allow_html=True)

    # ✅ EXPORT CARD
    st.markdown('<div class="card">', unsafe_allow_html=True)

    error_df = df[df["Is_Invalid"]]

    st.download_button(
        "Download Errors CSV",
        error_df.to_csv(index=False).encode("utf-8"),
        "errors.csv"
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        fixed_df.to_excel(tmp.name, index=False)
        file_data = open(tmp.name, "rb").read()

    st.download_button(
        "Download Corrected File",
        file_data,
        "corrected.xlsx"
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # ✅ UNIQUE PAIRS
    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.subheader("Unique Pairs")
    st.dataframe(unique_pairs, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)


