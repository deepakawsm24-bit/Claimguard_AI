
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="ClaimGuard AI",
    page_icon="🏥",
    layout="wide"
)

REQUIRED_DOCS = [
    "Discharge Summary",
    "Final Bill",
    "Investigation Reports"
]

VALID_TRUE = {"true", "yes", "1", "received"}
VALID_FALSE = {"false", "no", "0", "not received"}


def normalize_document(value):
    """Return True/False for valid values; None for invalid or missing."""
    if isinstance(value, bool):
        return value

    if pd.isna(value):
        return None

    value = str(value).strip().lower()

    if value in VALID_TRUE:
        return True
    if value in VALID_FALSE:
        return False

    return None


def assess_risk(row):
    """Calculate risk only when all document values are valid."""
    if row[REQUIRED_DOCS].isna().any():
        return pd.Series(["INVALID DATA", "Check invalid document values"])

    missing = [
        doc for doc in REQUIRED_DOCS
        if row[doc] is False
    ]

    if len(missing) >= 2:
        risk = "HIGH"
    elif len(missing) == 1:
        risk = "MEDIUM"
    else:
        risk = "NO DOCUMENT FLAGS"

    return pd.Series([risk, ", ".join(missing) if missing else "None"])


st.title("🏥 ClaimGuard AI")
st.subheader("Healthcare Claims Review & Risk Dashboard")

st.info(
    "Demo application using document rules. "
    "It does not approve claims or determine fraud."
)

st.header("📂 Upload Claims File")
st.write("Required columns:")

st.code(
    "Claim ID, Discharge Summary, Final Bill, Investigation Reports"
)

uploaded_file = st.file_uploader(
    "Upload a CSV or Excel file",
    type=["csv", "xlsx"]
)

if uploaded_file is None:
    st.caption(
        "Upload a synthetic test file to start. "
        "Do not upload real patient records."
    )
    st.stop()

try:
    if uploaded_file.name.lower().endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

except Exception as error:
    st.error(f"Could not read file: {error}")
    st.stop()


df.columns = df.columns.astype(str).str.strip()

required_columns = ["Claim ID"] + REQUIRED_DOCS
missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    st.error("Missing columns: " + ", ".join(missing_columns))
    st.stop()

if df.empty:
    st.warning("The uploaded file contains no claim rows.")
    st.stop()


st.header("🔎 Data Quality Validation")

# Normalize Claim IDs for validation
claim_ids = df["Claim ID"].astype("string").str.strip()
blank_ids = claim_ids.isna() | claim_ids.eq("")
duplicate_ids = (
    claim_ids.notna()
    & claim_ids.ne("")
    & claim_ids.duplicated(keep=False)
)

if blank_ids.any():
    st.error(f"Blank Claim IDs found: {int(blank_ids.sum())}")
else:
    st.success("No blank Claim IDs found.")

if duplicate_ids.any():
    st.warning(
        f"Duplicate Claim IDs found: {int(duplicate_ids.sum())} rows"
    )
    st.dataframe(
        df.loc[duplicate_ids, ["Claim ID"]],
        use_container_width=True,
        hide_index=True
    )
else:
    st.success("No duplicate Claim IDs found.")


# Validate document values before risk calculation
invalid_masks = {}

for col in REQUIRED_DOCS:
    original = df[col]
    normalized = original.apply(normalize_document)
    invalid_mask = normalized.isna()

    invalid_masks[col] = invalid_mask
    df[col] = normalized

    if invalid_mask.any():
        st.error(
            f"{col}: {int(invalid_mask.sum())} invalid or missing value(s)."
        )
        st.write(
            "Invalid values:",
            original[invalid_mask].astype(str).unique().tolist()
        )
    else:
        st.success(f"{col}: all document values are valid.")


# Rows with blank IDs, duplicate IDs, or invalid document values
invalid_rows = blank_ids | duplicate_ids

for col in REQUIRED_DOCS:
    invalid_rows = invalid_rows | invalid_masks[col]

df["Data Status"] = "VALID"
df.loc[invalid_rows, "Data Status"] = "REVIEW REQUIRED"

# Risk is calculated only for rows that pass validation
df["Risk Level"] = "NOT CALCULATED"
df["Missing Documents"] = "Resolve data issues first"

valid_rows = ~invalid_rows

if valid_rows.any():
    valid_results = df.loc[valid_rows].apply(assess_risk, axis=1)
    df.loc[valid_rows, ["Risk Level", "Missing Documents"]] = (
        valid_results.to_numpy()
    )


st.divider()
st.header("📊 Claims Summary")

total = len(df)
review_count = int((df["Data Status"] == "REVIEW REQUIRED").sum())
high = int((df["Risk Level"] == "HIGH").sum())
medium = int((df["Risk Level"] == "MEDIUM").sum())
clear = int((df["Risk Level"] == "NO DOCUMENT FLAGS").sum())

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Claims", total)
c2.metric("Needs Data Review", review_count)
c3.metric("High Risk", high)
c4.metric("Medium Risk", medium)
c5.metric("No Document Flags", clear)

st.subheader("📈 Claims by Risk Level")

risk_counts = df["Risk Level"].value_counts()
if not risk_counts.empty:
    st.bar_chart(risk_counts)


st.divider()
st.header("📋 Claim Review Results")

search_id = st.text_input("Search by Claim ID")

risk_options = [
    "ALL",
    "HIGH",
    "MEDIUM",
    "NO DOCUMENT FLAGS",
    "NOT CALCULATED"
]
risk_filter = st.selectbox("Filter by Risk Level", risk_options)

view = df.copy()

if search_id.strip():
    view = view[
        view["Claim ID"].astype(str).str.contains(
            search_id.strip(), case=False, na=False
        )
    ]

if risk_filter != "ALL":
    view = view[view["Risk Level"] == risk_filter]

st.dataframe(view, use_container_width=True, hide_index=True)


# Download all results, including data validation flags
csv_data = df.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    "⬇️ Download All Review Results (CSV)",
    data=csv_data,
    file_name="claim_review_results.csv",
    mime="text/csv"
)

# Download rows that require data review
review_data = df[df["Data Status"] == "REVIEW REQUIRED"]
review_csv = review_data.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    "⬇️ Download Data Review Issues (CSV)",
    data=review_csv,
    file_name="claim_data_review_issues.csv",
    mime="text/csv"
)

st.caption(
    "Demo only. Duplicate IDs, blank IDs, and invalid document values "
    "are flagged for review and excluded from risk classification. "
    "Authorized staff must verify all claims and make final decisions."
)
