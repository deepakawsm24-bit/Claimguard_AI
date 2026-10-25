
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="ClaimGuard AI | Advanced Analytics",
    page_icon="🏥",
    layout="wide"
)

REQUIRED_DOCS = [
    "Discharge Summary",
    "Final Bill",
    "Investigation Reports"
]

TRUE_VALUES = {"true", "yes", "1", "received"}
FALSE_VALUES = {"false", "no", "0", "not received"}

DATE_CANDIDATES = [
    "Claim Date", "Date", "Admission Date",
    "Discharge Date", "Submission Date", "Created At"
]

AMOUNT_CANDIDATES = [
    "Claim Amount", "Bill Amount", "Total Amount", "Amount"
]


def normalize_document(value):
    if isinstance(value, bool):
        return value

    if pd.isna(value):
        return None

    text = str(value).strip().lower()

    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False

    return None


def calculate_risk(row):
    if row[REQUIRED_DOCS].isna().any():
        return pd.Series([
            "NOT CALCULATED",
            "Resolve invalid or missing document values first"
        ])

    missing = [
        doc for doc in REQUIRED_DOCS
        if row[doc] is False
    ]

    if len(missing) >= 2:
        level = "HIGH"
    elif len(missing) == 1:
        level = "MEDIUM"
    else:
        level = "NO DOCUMENT FLAGS"

    missing_text = ", ".join(missing) if missing else "None"
    return pd.Series([level, missing_text])


def find_column(columns, candidates):
    lookup = {str(col).strip().lower(): col for col in columns}

    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    return None


st.title("🏥 ClaimGuard AI")
st.subheader("Advanced Healthcare Claims Analytics")

st.caption(
    "Rule-based demonstration for claim document review. "
    "Risk flags are not proof of fraud and do not approve or reject claims."
)

with st.sidebar:
    st.header("📂 Upload Claims File")
    uploaded_file = st.file_uploader(
        "Upload CSV or Excel",
        type=["csv", "xlsx"]
    )

    st.divider()
    st.caption("Use synthetic test data only. Do not upload real patient records.")


if uploaded_file is None:
    st.info("Upload a CSV or Excel file to open the analytics dashboard.")
    st.markdown("### Required columns")
    st.code(
        "Claim ID, Discharge Summary, Final Bill, Investigation Reports"
    )
    st.markdown(
        "Optional columns: Claim Date, Admission Date, "
        "Discharge Date, Claim Amount"
    )
    st.stop()


try:
    if uploaded_file.name.lower().endswith(".csv"):
        raw_df = pd.read_csv(uploaded_file)
    else:
        raw_df = pd.read_excel(uploaded_file)

except Exception as error:
    st.error(f"Could not read the uploaded file: {error}")
    st.stop()


raw_df.columns = raw_df.columns.astype(str).str.strip()

required_columns = ["Claim ID"] + REQUIRED_DOCS
missing_columns = [
    col for col in required_columns
    if col not in raw_df.columns
]

if missing_columns:
    st.error("Missing required columns: " + ", ".join(missing_columns))
    st.stop()

if raw_df.empty:
    st.warning("The uploaded file contains no claim rows.")
    st.stop()


df = raw_df.copy()
df["Claim ID"] = df["Claim ID"].astype("string").str.strip()

blank_ids = df["Claim ID"].isna() | df["Claim ID"].eq("")
duplicate_ids = (
    df["Claim ID"].notna()
    & df["Claim ID"].ne("")
    & df["Claim ID"].duplicated(keep=False)
)

# Normalize document columns and record invalid values
invalid_masks = {}

for col in REQUIRED_DOCS:
    original = df[col].copy()
    normalized = original.apply(normalize_document)
    invalid_masks[col] = normalized.isna()
    df[col] = normalized


# Data quality checks
st.header("🔎 Data Quality Validation")

quality1, quality2, quality3 = st.columns(3)

quality1.metric("Blank Claim IDs", int(blank_ids.sum()))
quality2.metric("Rows with Duplicate IDs", int(duplicate_ids.sum()))

invalid_document_rows = pd.Series(False, index=df.index)
for col in REQUIRED_DOCS:
    invalid_document_rows |= invalid_masks[col]

quality3.metric(
    "Rows with Invalid Documents",
    int(invalid_document_rows.sum())
)

with st.expander("View data quality details"):
    if blank_ids.any():
        st.warning(f"{int(blank_ids.sum())} row(s) have blank Claim IDs.")
    else:
        st.success("No blank Claim IDs found.")

    if duplicate_ids.any():
        st.warning(
            f"{int(duplicate_ids.sum())} row(s) have duplicate Claim IDs."
        )
        st.dataframe(
            raw_df.loc[duplicate_ids, ["Claim ID"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("No duplicate Claim IDs found.")

    for col in REQUIRED_DOCS:
        bad = invalid_masks[col]
        if bad.any():
            st.error(
                f"{col}: {int(bad.sum())} invalid or missing value(s)."
            )
            st.write(
                "Values needing correction:",
                raw_df.loc[bad, col].astype(str).unique().tolist()
            )
        else:
            st.success(f"{col}: all values are valid.")


# Invalid or duplicate rows must not receive a calculated risk level
review_mask = blank_ids | duplicate_ids | invalid_document_rows

df["Data Status"] = "VALID"
df.loc[review_mask, "Data Status"] = "REVIEW REQUIRED"

df["Risk Level"] = "NOT CALCULATED"
df["Missing Documents"] = "Resolve data issues first"

valid_mask = ~review_mask

if valid_mask.any():
    calculated = df.loc[valid_mask].apply(calculate_risk, axis=1)
    df.loc[valid_mask, ["Risk Level", "Missing Documents"]] = (
        calculated.to_numpy()
    )


# Dashboard overview
st.divider()
st.header("📊 Executive Dashboard")

total_claims = len(df)
review_count = int((df["Data Status"] == "REVIEW REQUIRED").sum())
high_count = int((df["Risk Level"] == "HIGH").sum())
medium_count = int((df["Risk Level"] == "MEDIUM").sum())
clear_count = int((df["Risk Level"] == "NO DOCUMENT FLAGS").sum())
calculated_count = int(df["Risk Level"].isin(
    ["HIGH", "MEDIUM", "NO DOCUMENT FLAGS"]
).sum())

high_pct = (
    high_count / calculated_count * 100
    if calculated_count else 0
)

k1, k2, k3 = st.columns(3)
k1.metric("Total Claims", total_claims)
k2.metric("Needs Data Review", review_count)
k3.metric("Claims Risk-Calculated", calculated_count)

k4, k5, k6 = st.columns(3)
k4.metric("High Risk", high_count)
k5.metric("Medium Risk", medium_count)
k6.metric("No Document Flags", clear_count)

st.metric(
    "High-Risk Share of Calculated Claims",
    f"{high_pct:.1f}%",
    help="High-risk claims divided by claims with a calculated risk level."
)


# Analytics tabs
tab_overview, tab_docs, tab_trends, tab_records = st.tabs([
    "📈 Risk Overview",
    "📑 Document Analytics",
    "📅 Trends & Amounts",
    "🔍 Claim Explorer"
])


with tab_overview:
    st.subheader("Claims by Risk Level")

    risk_order = [
        "HIGH", "MEDIUM", "NO DOCUMENT FLAGS", "NOT CALCULATED"
    ]
    risk_counts = (
        df["Risk Level"]
        .value_counts()
        .reindex(risk_order, fill_value=0)
    )

    st.bar_chart(risk_counts)

    left, right = st.columns(2)

    with left:
        st.subheader("Data Status")
        status_counts = df["Data Status"].value_counts()
        st.bar_chart(status_counts)

    with right:
        st.subheader("Risk Summary")
        summary = pd.DataFrame({
            "Risk Level": risk_order,
            "Claims": [int(risk_counts[level]) for level in risk_order]
        })
        st.dataframe(summary, use_container_width=True, hide_index=True)


with tab_docs:
    st.subheader("Document Availability")

    st.caption(
        "Missing rate is calculated only from rows with valid document values. "
        "Invalid values are excluded from each document's denominator."
    )

    doc_stats = []

    for col in REQUIRED_DOCS:
        valid_doc_values = df[col].notna()
        valid_count = int(valid_doc_values.sum())
        missing_count = int((df[col] == False).sum())  # noqa: E712
        received_count = int((df[col] == True).sum())  # noqa: E712
        missing_rate = (
            missing_count / valid_count * 100 if valid_count else 0
        )

        doc_stats.append({
            "Document": col,
            "Received": received_count,
            "Missing": missing_count,
            "Valid Values": valid_count,
            "Missing Rate (%)": round(missing_rate, 1)
        })

    doc_df = pd.DataFrame(doc_stats)

    st.dataframe(doc_df, use_container_width=True, hide_index=True)

    st.subheader("Missing Documents by Type")
    st.bar_chart(doc_df.set_index("Document")["Missing"])

    st.subheader("Document Missing Rate (%)")
    st.bar_chart(doc_df.set_index("Document")["Missing Rate (%)"])


with tab_trends:
    st.subheader("Monthly Claim Trends")

    date_col = find_column(df.columns, DATE_CANDIDATES)

    if date_col:
        dates = pd.to_datetime(df[date_col], errors="coerce")
        dated = df.loc[dates.notna()].copy()
        dated["Parsed Date"] = dates[dates.notna()]
        
        if not dated.empty:
            dated["Month"] = (
                dated["Parsed Date"].dt.to_period("M").astype(str)
            )
            monthly = dated.groupby("Month").size().rename("Claims")
            st.line_chart(monthly)
            st.caption(f"Date column used: {date_col}")
        else:
            st.info(
                f"Column '{date_col}' was found, but no valid dates were detected."
            )
    else:
        st.info(
            "Monthly trends are not available because no recognized date column "
            "was found. Add a column such as Claim Date or Admission Date."
        )

    st.divider()
    st.subheader("Claim Amount Analysis")

    amount_col = find_column(df.columns, AMOUNT_CANDIDATES)

    if amount_col:
        amounts = pd.to_numeric(df[amount_col], errors="coerce")
        amount_data = df.loc[amounts.notna()].copy()
        amount_data["Parsed Amount"] = amounts[amounts.notna()]

        if not amount_data.empty:
            a1, a2, a3 = st.columns(3)
            a1.metric(
                "Total Amount",
                f"{amount_data['Parsed Amount'].sum():,.2f}"
            )
            a2.metric(
                "Average Amount",
                f"{amount_data['Parsed Amount'].mean():,.2f}"
            )
            a3.metric(
                "Largest Amount",
                f"{amount_data['Parsed Amount'].max():,.2f}"
            )

            st.bar_chart(
                amount_data.set_index("Claim ID")["Parsed Amount"]
            )
            st.caption(f"Amount column used: {amount_col}")
        else:
            st.info("The amount column has no valid numeric values.")
    else:
        st.info(
            "Amount analytics are unavailable. Add a column such as "
            "'Claim Amount' or 'Bill Amount' to enable them."
        )


with tab_records:
    st.subheader("Interactive Claim Explorer")

    f1, f2 = st.columns(2)

    with f1:
        search_text = st.text_input("Search Claim ID")

    with f2:
        selected_risks = st.multiselect(
            "Filter by Risk Level",
            options=[
                "HIGH", "MEDIUM", "NO DOCUMENT FLAGS", "NOT CALCULATED"
            ],
            default=[
                "HIGH", "MEDIUM", "NO DOCUMENT FLAGS", "NOT CALCULATED"
            ]
        )

    selected_status = st.multiselect(
        "Filter by Data Status",
        options=["VALID", "REVIEW REQUIRED"],
        default=["VALID", "REVIEW REQUIRED"]
    )

    filtered = df.copy()

    if search_text.strip():
        filtered = filtered[
            filtered["Claim ID"].astype(str).str.contains(
                search_text.strip(), case=False, na=False
            )
        ]

    filtered = filtered[filtered["Risk Level"].isin(selected_risks)]
    filtered = filtered[filtered["Data Status"].isin(selected_status)]

    st.write(f"Showing **{len(filtered)}** of **{len(df)}** rows.")

    display_columns = (
        ["Claim ID"]
        + REQUIRED_DOCS
        + ["Risk Level", "Missing Documents", "Data Status"]
    )

    st.dataframe(
        filtered[display_columns],
        use_container_width=True,
        hide_index=True
    )

    filtered_csv = filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Download Filtered Results (CSV)",
        data=filtered_csv,
        file_name="claimguard_filtered_results.csv",
        mime="text/csv"
    )


st.divider()
st.subheader("📥 Export Reports")

full_csv = df.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "Download All Review Results (CSV)",
    data=full_csv,
    file_name="claimguard_all_results.csv",
    mime="text/csv"
)

issues = df[df["Data Status"] == "REVIEW REQUIRED"]
issues_csv = issues.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    "Download Data Quality Issues (CSV)",
    data=issues_csv,
    file_name="claimguard_data_quality_issues.csv",
    mime="text/csv"
)

st.caption(
    "ClaimGuard AI is a rule-based demo. Risk flags support manual review only. "
    "Authorized staff must verify claims and make all final decisions."
)
