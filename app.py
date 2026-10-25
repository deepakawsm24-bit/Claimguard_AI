
import io
from datetime import datetime

import pandas as pd
import streamlit as st

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak
)

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

    missing = [doc for doc in REQUIRED_DOCS if row[doc] is False]

    if len(missing) >= 2:
        level = "HIGH"
    elif len(missing) == 1:
        level = "MEDIUM"
    else:
        level = "NO DOCUMENT FLAGS"

    return pd.Series([
        level,
        ", ".join(missing) if missing else "None"
    ])


def find_column(columns, candidates):
    lookup = {str(col).strip().lower(): col for col in columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    return None


def make_pdf(data, document_stats, metrics, source_name):
    """Create a downloadable PDF summary report."""
    output = io.BytesIO()

    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=21,
        leading=26,
        textColor=colors.HexColor("#163A5F"),
        spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name="SmallCell",
        parent=styles["BodyText"],
        fontSize=7,
        leading=9,
        wordWrap="CJK"
    ))

    story = []

    story.append(Paragraph("ClaimGuard AI", styles["ReportTitle"]))
    story.append(Paragraph(
        "Healthcare Claims Review & Analytics Report",
        ParagraphStyle(
            name="Subtitle",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            fontSize=12,
            spaceAfter=8
        )
    ))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}",
        styles["Normal"]
    ))
    story.append(Paragraph(
        f"Source file: {source_name}",
        styles["Normal"]
    ))
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("1. Executive Summary", styles["Heading2"]))

    summary_data = [
        ["Metric", "Count / Value"],
        ["Total Claims", str(metrics["total"])],
        ["Needs Data Review", str(metrics["review"])],
        ["High Risk", str(metrics["high"])],
        ["Medium Risk", str(metrics["medium"])],
        ["No Document Flags", str(metrics["clear"])],
        ["Risk Calculated", str(metrics["calculated"])],
        ["High-Risk Share", f"{metrics['high_pct']:.1f}%"]
    ]

    summary_table = Table(summary_data, colWidths=[75 * mm, 45 * mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#163A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F1F5F9")]),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 7 * mm))

    story.append(Paragraph("2. Document Availability", styles["Heading2"]))

    doc_data = [[
        "Document", "Received", "Missing",
        "Valid Values", "Missing Rate (%)"
    ]]

    for item in document_stats:
        doc_data.append([
            item["Document"],
            str(item["Received"]),
            str(item["Missing"]),
            str(item["Valid Values"]),
            f"{item['Missing Rate (%)']:.1f}%"
        ])

    doc_table = Table(
        doc_data,
        colWidths=[75 * mm, 25 * mm, 25 * mm, 30 * mm, 40 * mm],
        repeatRows=1
    )
    doc_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#163A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F1F5F9")]),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(doc_table)
    story.append(Spacer(1, 7 * mm))

    story.append(Paragraph("3. Claim Review Details", styles["Heading2"]))

    review_columns = [
        "Claim ID", "Risk Level", "Data Status", "Missing Documents"
    ]
    review_data = [[
        Paragraph(column, styles["SmallCell"])
        for column in review_columns
    ]]

    for _, row in data.iterrows():
        review_data.append([
            Paragraph(str(row.get("Claim ID", "")), styles["SmallCell"]),
            Paragraph(str(row.get("Risk Level", "")), styles["SmallCell"]),
            Paragraph(str(row.get("Data Status", "")), styles["SmallCell"]),
            Paragraph(str(row.get("Missing Documents", "")), styles["SmallCell"])
        ])

    review_table = Table(
        review_data,
        colWidths=[35 * mm, 38 * mm, 43 * mm, 105 * mm],
        repeatRows=1
    )
    review_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#163A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F1F5F9")]),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(review_table)
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("4. Important Notes", styles["Heading2"]))
    story.append(Paragraph(
        "This is a rule-based demonstration. Risk levels flag missing "
        "documents for manual review; they do not establish fraud and do "
        "not approve or reject claims. Duplicate IDs, blank IDs and invalid "
        "document values require review. Final decisions must be made by "
        "authorized healthcare staff. This report contains data from the "
        "uploaded file, so use synthetic test data only.",
        styles["BodyText"]
    ))

    def add_page_number(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(
            landscape(A4)[0] - 14 * mm,
            7 * mm,
            f"ClaimGuard AI | Page {document.page}"
        )
        canvas.restoreState()

    doc.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number
    )

    output.seek(0)
    return output.getvalue()


st.title("🏥 ClaimGuard AI")
st.subheader("Advanced Healthcare Claims Analytics")
st.caption(
    "Rule-based demonstration. Risk flags support manual review only."
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
    st.info("Upload a CSV or Excel file to open the dashboard.")
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
    st.error(f"Could not read uploaded file: {error}")
    st.stop()


raw_df.columns = raw_df.columns.astype(str).str.strip()

required_columns = ["Claim ID"] + REQUIRED_DOCS
missing_columns = [
    col for col in required_columns if col not in raw_df.columns
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

invalid_masks = {}

for col in REQUIRED_DOCS:
    normalized = df[col].apply(normalize_document)
    invalid_masks[col] = normalized.isna()
    df[col] = normalized


st.header("🔎 Data Quality Validation")

q1, q2, q3 = st.columns(3)
q1.metric("Blank Claim IDs", int(blank_ids.sum()))
q2.metric("Duplicate-ID Rows", int(duplicate_ids.sum()))

invalid_document_rows = pd.Series(False, index=df.index)
for col in REQUIRED_DOCS:
    invalid_document_rows |= invalid_masks[col]

q3.metric("Rows with Invalid Documents", int(invalid_document_rows.sum()))

with st.expander("View data quality details"):
    if blank_ids.any():
        st.warning(f"Blank Claim IDs: {int(blank_ids.sum())}")
    else:
        st.success("No blank Claim IDs found.")

    if duplicate_ids.any():
        st.warning(f"Duplicate-ID rows: {int(duplicate_ids.sum())}")
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
            st.error(f"{col}: {int(bad.sum())} invalid or missing value(s).")
            st.write(
                raw_df.loc[bad, col].astype(str).unique().tolist()
            )
        else:
            st.success(f"{col}: all document values are valid.")


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


total = len(df)
review_count = int((df["Data Status"] == "REVIEW REQUIRED").sum())
high_count = int((df["Risk Level"] == "HIGH").sum())
medium_count = int((df["Risk Level"] == "MEDIUM").sum())
clear_count = int((df["Risk Level"] == "NO DOCUMENT FLAGS").sum())
calculated_count = int(
    df["Risk Level"].isin(
        ["HIGH", "MEDIUM", "NO DOCUMENT FLAGS"]
    ).sum()
)
high_pct = high_count / calculated_count * 100 if calculated_count else 0


doc_stats = []
for col in REQUIRED_DOCS:
    valid_values = df[col].notna()
    valid_count = int(valid_values.sum())
    missing_count = int((df[col] == False).sum())  # noqa: E712
    received_count = int((df[col] == True).sum())  # noqa: E712
    missing_rate = missing_count / valid_count * 100 if valid_count else 0

    doc_stats.append({
        "Document": col,
        "Received": received_count,
        "Missing": missing_count,
        "Valid Values": valid_count,
        "Missing Rate (%)": round(missing_rate, 1)
    })


st.divider()
st.header("📊 Executive Dashboard")

k1, k2, k3 = st.columns(3)
k1.metric("Total Claims", total)
k2.metric("Needs Data Review", review_count)
k3.metric("Claims Risk-Calculated", calculated_count)

k4, k5, k6 = st.columns(3)
k4.metric("High Risk", high_count)
k5.metric("Medium Risk", medium_count)
k6.metric("No Document Flags", clear_count)

st.metric("High-Risk Share of Calculated Claims", f"{high_pct:.1f}%")


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
    risk_counts = df["Risk Level"].value_counts().reindex(
        risk_order, fill_value=0
    )
    st.bar_chart(risk_counts)

    left, right = st.columns(2)
    with left:
        st.subheader("Data Status")
        st.bar_chart(df["Data Status"].value_counts())

    with right:
        st.subheader("Risk Summary")
        st.dataframe(
            pd.DataFrame({
                "Risk Level": risk_order,
                "Claims": [int(risk_counts[level]) for level in risk_order]
            }),
            use_container_width=True,
            hide_index=True
        )


with tab_docs:
    st.subheader("Document Availability")
    st.caption(
        "Missing rates use only rows with valid document values."
    )
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
            dated["Month"] = dated["Parsed Date"].dt.to_period("M").astype(str)
            st.line_chart(dated.groupby("Month").size().rename("Claims"))
            st.caption(f"Date column used: {date_col}")
        else:
            st.info(f"No valid dates detected in '{date_col}'.")
    else:
        st.info(
            "Add a date column such as Claim Date or Admission Date "
            "to enable monthly trends."
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
            a1.metric("Total Amount", f"{amount_data['Parsed Amount'].sum():,.2f}")
            a2.metric("Average Amount", f"{amount_data['Parsed Amount'].mean():,.2f}")
            a3.metric("Largest Amount", f"{amount_data['Parsed Amount'].max():,.2f}")
            st.bar_chart(amount_data.set_index("Claim ID")["Parsed Amount"])
        else:
            st.info("No valid numeric values found in the amount column.")
    else:
        st.info(
            "Add Claim Amount or Bill Amount to enable amount analytics."
        )


with tab_records:
    st.subheader("Interactive Claim Explorer")

    f1, f2 = st.columns(2)
    with f1:
        search_text = st.text_input("Search Claim ID")
    with f2:
        selected_risks = st.multiselect(
            "Filter by Risk Level",
            ["HIGH", "MEDIUM", "NO DOCUMENT FLAGS", "NOT CALCULATED"],
            default=["HIGH", "MEDIUM", "NO DOCUMENT FLAGS", "NOT CALCULATED"]
        )

    selected_status = st.multiselect(
        "Filter by Data Status",
        ["VALID", "REVIEW REQUIRED"],
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

    st.write(f"Showing {len(filtered)} of {len(df)} rows.")

    display_columns = (
        ["Claim ID"] + REQUIRED_DOCS
        + ["Risk Level", "Missing Documents", "Data Status"]
    )
    st.dataframe(
        filtered[display_columns],
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "⬇️ Download Filtered Results (CSV)",
        data=filtered.to_csv(index=False).encode("utf-8-sig"),
        file_name="claimguard_filtered_results.csv",
        mime="text/csv"
    )


st.divider()
st.header("📥 Export Reports")

st.download_button(
    "Download All Review Results (CSV)",
    data=df.to_csv(index=False).encode("utf-8-sig"),
    file_name="claimguard_all_results.csv",
    mime="text/csv"
)

issues = df[df["Data Status"] == "REVIEW REQUIRED"]
st.download_button(
    "Download Data Quality Issues (CSV)",
    data=issues.to_csv(index=False).encode("utf-8-sig"),
    file_name="claimguard_data_quality_issues.csv",
    mime="text/csv"
)


st.divider()
st.header("📄 PDF Report Generator")
st.write(
    "Generate a report with executive metrics, document availability, "
    "data-quality review status and claim-level results."
)

metrics = {
    "total": total,
    "review": review_count,
    "high": high_count,
    "medium": medium_count,
    "clear": clear_count,
    "calculated": calculated_count,
    "high_pct": high_pct
}

try:
    pdf_bytes = make_pdf(
        df,
        doc_stats,
        metrics,
        uploaded_file.name
    )

    st.download_button(
        "⬇️ Download Professional PDF Report",
        data=pdf_bytes,
        file_name="ClaimGuard_AI_Claims_Report.pdf",
        mime="application/pdf"
    )
    st.success("Your PDF report is ready to download.")

except Exception as error:
    st.error(f"Could not generate PDF report: {error}")


st.caption(
    "Demo only. Risk flags support manual review and do not establish fraud. "
    "Authorized staff must make all final claim decisions. "
    "Use synthetic data only."
)
