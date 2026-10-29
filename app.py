import io
import html
from datetime import datetime

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)


# ---------------------------------------------------------------------
# ClaimGuard AI | Professional healthcare claims review dashboard
# Rule-based demonstration only — not a fraud-detection or adjudication tool.
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="ClaimGuard AI | Claims Intelligence",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

REQUIRED_DOCS = ["Discharge Summary", "Final Bill", "Investigation Reports"]
TRUE_VALUES = {"true", "yes", "1", "received", "available", "present"}
FALSE_VALUES = {"false", "no", "0", "not received", "missing", "not available", "absent"}
DATE_CANDIDATES = ["Claim Date", "Date", "Admission Date", "Discharge Date", "Submission Date", "Created At"]
AMOUNT_CANDIDATES = ["Claim Amount", "Bill Amount", "Total Amount", "Amount"]


# ---------------------------------------------------------------------
# ClaimGuard AI | Explainable claim consistency checks
# Rule-based assistance only; findings require human review.
# ---------------------------------------------------------------------
def run_claim_consistency_checks(row):
    findings = []

    # 1. Check required document availability
    for doc in REQUIRED_DOCS:
        if doc not in row.index:
            findings.append({
                "Check": "Document column missing",
                "Finding": f"Required column '{doc}' is not present.",
                "Severity": "HIGH",
            })
            continue

        value = row[doc]

        if pd.isna(value):
            missing = True
        else:
            text = str(value).strip().lower()
            missing = text in FALSE_VALUES or text in {
                "", "nan", "none", "null", "n/a", "na"
            }

        if missing:
            findings.append({
                "Check": "Document availability",
                "Finding": f"{doc} is missing or marked unavailable.",
                "Severity": "REVIEW",
            })

    # 2. Compare amount columns only when multiple are supplied
    available_amounts = {}

    for col in AMOUNT_CANDIDATES:
        if col in row.index and pd.notna(row[col]):
            value = pd.to_numeric(row[col], errors="coerce")
            if pd.notna(value):
                available_amounts[col] = float(value)

    if len(available_amounts) >= 2:
        values = list(available_amounts.values())

        if max(values) - min(values) > 1.0:
            details = ", ".join(
                f"{name}: {value:,.2f}"
                for name, value in available_amounts.items()
            )
            findings.append({
                "Check": "Amount consistency",
                "Finding": (
                    "Amount fields differ; verify the source documents. "
                    + details
                ),
                "Severity": "REVIEW",
            })

    # 3. Check admission and discharge date order
    if "Admission Date" in row.index and "Discharge Date" in row.index:
        admission = pd.to_datetime(
            row["Admission Date"], errors="coerce"
        )
        discharge = pd.to_datetime(
            row["Discharge Date"], errors="coerce"
        )

        if pd.notna(admission) and pd.notna(discharge):
            if discharge < admission:
                findings.append({
                    "Check": "Date consistency",
                    "Finding": (
                        "Discharge date is earlier than admission date."
                    ),
                    "Severity": "REVIEW",
                })

    if not findings:
        findings.append({
            "Check": "Basic consistency",
            "Finding": (
                "No issues detected by the configured checks. "
                "This does not confirm that the claim is correct."
            ),
            "Severity": "INFO",
        })

    return findings

# Visual theme
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
:root { --cg-navy:#142b4a; --cg-blue:#2563eb; --cg-teal:#0f766e; --cg-bg:#f5f7fb; }
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: var(--cg-bg); }
.block-container { padding-top: 1.6rem; padding-bottom: 2.4rem; max-width: 1500px; }
[data-testid="stSidebar"] { background: #10233f; }
[data-testid="stSidebar"] * { color: #f4f7fb !important; }
[data-testid="stSidebar"] [data-testid="stFileUploader"] section { background: #1a3558; border-color: #4c6585; }
.cg-hero { padding: 1.45rem 1.65rem; border-radius: 18px; color: white;
 background: linear-gradient(120deg,#10233f 0%,#1b4675 58%,#2563eb 100%);
 box-shadow: 0 12px 30px rgba(20,43,74,.13); margin-bottom: 1.15rem; }
.cg-eyebrow { font-size:.76rem; letter-spacing:.13em; text-transform:uppercase; opacity:.78; font-weight:700; }
.cg-title { font-family:'Manrope',sans-serif; font-size:2rem; font-weight:800; margin:.18rem 0 .25rem 0; line-height:1.2; }
.cg-subtitle { opacity:.88; font-size:.98rem; }
.cg-chip { display:inline-block; border:1px solid rgba(255,255,255,.28); border-radius:99px;
 padding:.28rem .7rem; font-size:.76rem; margin-top:.75rem; background:rgba(255,255,255,.08); }
.section-label { color:#52627a; text-transform:uppercase; letter-spacing:.11em; font-size:.72rem; font-weight:700; margin-bottom:.15rem; }
.section-title { color:#142b4a; font-family:'Manrope',sans-serif; font-size:1.22rem; font-weight:800; margin:.1rem 0 .7rem 0; }
div[data-testid="stMetric"] { background:#fff; border:1px solid #e4eaf2; padding:1rem 1.05rem; border-radius:14px; box-shadow:0 4px 14px rgba(20,43,74,.035); }
div[data-testid="stMetricLabel"] { color:#61718a; font-weight:600; }
div[data-testid="stMetricValue"] { color:#142b4a; font-family:'Manrope',sans-serif; font-weight:800; }
.stTabs [data-baseweb="tab-list"] { gap: .45rem; }
.stTabs [data-baseweb="tab"] { background:#e9eef6; border-radius:9px 9px 0 0; padding:.65rem 1rem; }
.stTabs [aria-selected="true"] { background:white !important; }
div[data-testid="stDataFrame"] { border:1px solid #e4eaf2; border-radius:12px; overflow:hidden; }
div.stButton > button, div.stDownloadButton > button { border-radius:9px; font-weight:700; }
.small-note { color:#64748b; font-size:.83rem; }
</style>
""", unsafe_allow_html=True)


def normalize_document(value):
    """Normalize common spreadsheet representations to True, False or None."""
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    text = str(value).strip().lower()
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    return None


def calculate_risk(row):
    if row[REQUIRED_DOCS].isna().any():
        return pd.Series(["NOT CALCULATED", "Resolve invalid or missing document values first"])
    missing = [doc for doc in REQUIRED_DOCS if row[doc] == False]  # noqa: E712
    if len(missing) >= 2:
        level = "HIGH"
    elif len(missing) == 1:
        level = "MEDIUM"
    else:
        level = "NO DOCUMENT FLAGS"
    return pd.Series([level, ", ".join(missing) if missing else "None"])


def find_column(columns, candidates):
    lookup = {str(col).strip().lower(): col for col in columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    return None


def make_pdf(data, document_stats, metrics, source_name):
    """Create a downloadable landscape PDF report."""
    output = io.BytesIO()
    pdf = SimpleDocTemplate(
        output, pagesize=landscape(A4),
        rightMargin=13 * mm, leftMargin=13 * mm,
        topMargin=12 * mm, bottomMargin=14 * mm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="CGTitle", parent=styles["Title"], alignment=TA_CENTER,
        fontName="Helvetica-Bold", fontSize=22, leading=26,
        textColor=colors.HexColor("#142B4A"), spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name="CGSub", parent=styles["Normal"], alignment=TA_CENTER,
        fontSize=10, textColor=colors.HexColor("#52627A"), spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="CGCell", parent=styles["BodyText"], fontSize=7, leading=8.5,
        wordWrap="CJK",
    ))
    story = [
        Paragraph("ClaimGuard AI", styles["CGTitle"]),
        Paragraph("Healthcare Claims Review & Analytics Report", styles["CGSub"]),
        Paragraph(
            f"<b>Generated:</b> {datetime.now().strftime('%d %b %Y, %I:%M %p')} "
            f"&nbsp;&nbsp; <b>Source file:</b> {html.escape(str(source_name))}",
            styles["Normal"],
        ),
        Spacer(1, 7 * mm),
        Paragraph("1. Executive Summary", styles["Heading2"]),
    ]

    summary = [
        ["Metric", "Count / Value"],
        ["Total claims", str(metrics["total"])],
        ["Needs data review", str(metrics["review"])],
        ["High risk", str(metrics["high"])],
        ["Medium risk", str(metrics["medium"])],
        ["No document flags", str(metrics["clear"])],
        ["Risk calculated", str(metrics["calculated"])],
        ["High-risk share", f"{metrics['high_pct']:.1f}%"],
    ]
    t = Table(summary, colWidths=[72 * mm, 43 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#142B4A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#CFD8E3")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F6FA")]),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([t, Spacer(1, 6 * mm), Paragraph("2. Document Availability", styles["Heading2"])])

    doc_rows = [["Document", "Received", "Missing", "Valid values", "Missing rate (%)"]]
    for item in document_stats:
        doc_rows.append([
            item["Document"], str(item["Received"]), str(item["Missing"]),
            str(item["Valid Values"]), f'{item["Missing Rate (%)"]:.1f}%',
        ])
    dt = Table(doc_rows, colWidths=[75 * mm, 25 * mm, 25 * mm, 30 * mm, 38 * mm], repeatRows=1)
    dt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#142B4A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#CFD8E3")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F6FA")]),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([dt, Spacer(1, 6 * mm)])

    # Start the claim-level table on a fresh page for a cleaner report layout.
    story.extend([PageBreak(), Paragraph("3. Claim Review Details", styles["Heading2"])])

    cols = ["Claim ID", "Risk Level", "Data Status", "Missing Documents"]
    rows = [[Paragraph(c, styles["CGCell"]) for c in cols]]
    for _, row in data.iterrows():
        rows.append([
            Paragraph(html.escape(str(row.get("Claim ID", ""))), styles["CGCell"]),
            Paragraph(html.escape(str(row.get("Risk Level", ""))), styles["CGCell"]),
            Paragraph(html.escape(str(row.get("Data Status", ""))), styles["CGCell"]),
            Paragraph(html.escape(str(row.get("Missing Documents", ""))), styles["CGCell"]),
        ])

    rt = Table(
        rows,
        colWidths=[35 * mm, 38 * mm, 43 * mm, 105 * mm],
        repeatRows=1,
        splitByRow=1,
    )
    rt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#142B4A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), .3, colors.HexColor("#CFD8E3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F6FA")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([rt, Spacer(1, 6 * mm), Paragraph("4. Important Notes", styles["Heading2"])])
    story.append(Paragraph(
        "This is a rule-based demonstration. Risk levels flag missing documents for manual review; "
        "they do not establish fraud and do not approve or reject claims. Duplicate IDs, blank IDs "
        "and invalid document values require review. Final decisions must be made by authorized "
        "healthcare staff. Use synthetic test data only.",
        styles["BodyText"]
    ))
    def add_page_number(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawRightString(landscape(A4)[0] - 13 * mm, 7 * mm,
                               f"ClaimGuard AI  |  Page {document.page}")
        canvas.restoreState()
    pdf.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    output.seek(0)
    return output.getvalue()


def show_section(label, title):
    st.markdown(f'<div class="section-label">{label}</div><div class="section-title">{title}</div>', unsafe_allow_html=True)


# Sidebar
with st.sidebar:
    st.markdown("## 🏥 ClaimGuard AI")
    st.caption("Claims intelligence workspace")
    st.divider()
    st.markdown("### Upload claims data")
    uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx"])
    st.markdown("---")
    st.markdown("**Required columns**")
    st.code("Claim ID\nDischarge Summary\nFinal Bill\nInvestigation Reports", language="text")
    st.markdown("**Optional columns**")
    st.caption("Claim Date, Admission Date, Discharge Date, Claim Amount")
    st.divider()
    st.caption("Privacy note: use synthetic test data only. Do not upload real patient records.")


st.markdown("""
<div class="cg-hero">
  <div class="cg-eyebrow">Healthcare operations • Claims intelligence</div>
  <div class="cg-title">ClaimGuard AI</div>
  <div class="cg-subtitle">A clean, audit-friendly workspace for claims data quality, document completeness and review prioritisation.</div>
  <span class="cg-chip">RULE-BASED DEMONSTRATION</span>
</div>
""", unsafe_allow_html=True)

if uploaded_file is None:
    show_section("GET STARTED", "Turn claims data into actionable review insights")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Data validation", "Ready")
        st.caption("Identify blank IDs, duplicate IDs and invalid document values.")
    with c2:
        st.metric("Claims overview", "Ready")
        st.caption("Review claim counts by document-flag level and data status.")
    with c3:
        st.metric("Export centre", "Ready")
        st.caption("Download filtered CSV results and a PDF summary report.")
    st.info("Upload a CSV or Excel file from the sidebar to open the dashboard.")
    with st.expander("Example data format"):
        example = pd.DataFrame([
            {"Claim ID": "CLM-1001", "Discharge Summary": "Yes", "Final Bill": "Yes", "Investigation Reports": "Yes", "Claim Date": "2026-01-12", "Claim Amount": 18500},
            {"Claim ID": "CLM-1002", "Discharge Summary": "No", "Final Bill": "Yes", "Investigation Reports": "No", "Claim Date": "2026-01-15", "Claim Amount": 42000},
            {"Claim ID": "CLM-1003", "Discharge Summary": "Yes", "Final Bill": "No", "Investigation Reports": "Yes", "Claim Date": "2026-02-02", "Claim Amount": 27000},
        ])
        st.dataframe(example, use_container_width=True, hide_index=True)
        st.download_button("Download example CSV", example.to_csv(index=False).encode("utf-8-sig"),
                           file_name="claimguard_sample_data.csv", mime="text/csv")
    st.stop()

# Read uploaded file safely
try:
    if uploaded_file.name.lower().endswith(".csv"):
        raw_df = pd.read_csv(uploaded_file)
    else:
        raw_df = pd.read_excel(uploaded_file)
except Exception as error:
    st.error(f"Unable to read the uploaded file: {error}")
    st.stop()

raw_df.columns = raw_df.columns.astype(str).str.strip()
required_columns = ["Claim ID"] + REQUIRED_DOCS
missing_columns = [col for col in required_columns if col not in raw_df.columns]
if missing_columns:
    st.error("Missing required columns: " + ", ".join(missing_columns))
    st.info("Check the exact column names in the sidebar.")
    st.stop()
if raw_df.empty:
    st.warning("The uploaded file contains column headers but no claim rows.")
    st.stop()

df = raw_df.copy()
df["Claim ID"] = df["Claim ID"].astype("string").str.strip()
blank_ids = df["Claim ID"].isna() | df["Claim ID"].eq("")
duplicate_ids = df["Claim ID"].notna() & df["Claim ID"].ne("") & df["Claim ID"].duplicated(keep=False)

invalid_masks = {}
for col in REQUIRED_DOCS:
    normalized = df[col].apply(normalize_document)
    invalid_masks[col] = normalized.isna()
    df[col] = normalized

invalid_document_rows = pd.Series(False, index=df.index)
for col in REQUIRED_DOCS:
    invalid_document_rows |= invalid_masks[col]

review_mask = blank_ids | duplicate_ids | invalid_document_rows
df["Data Status"] = "VALID"
df.loc[review_mask, "Data Status"] = "REVIEW REQUIRED"
df["Risk Level"] = "NOT CALCULATED"
df["Missing Documents"] = "Resolve data issues first"

valid_mask = ~review_mask
if valid_mask.any():
    calculated = df.loc[valid_mask].apply(calculate_risk, axis=1)
    df.loc[valid_mask, ["Risk Level", "Missing Documents"]] = calculated.to_numpy()

total = len(df)
review_count = int((df["Data Status"] == "REVIEW REQUIRED").sum())
high_count = int((df["Risk Level"] == "HIGH").sum())
medium_count = int((df["Risk Level"] == "MEDIUM").sum())
clear_count = int((df["Risk Level"] == "NO DOCUMENT FLAGS").sum())
calculated_count = int(df["Risk Level"].isin(["HIGH", "MEDIUM", "NO DOCUMENT FLAGS"]).sum())
high_pct = high_count / calculated_count * 100 if calculated_count else 0

doc_stats = []
for col in REQUIRED_DOCS:
    valid_values = df[col].notna()
    valid_count = int(valid_values.sum())
    missing_count = int((df[col] == False).sum())  # noqa: E712
    received_count = int((df[col] == True).sum())  # noqa: E712
    missing_rate = missing_count / valid_count * 100 if valid_count else 0
    doc_stats.append({
        "Document": col, "Received": received_count, "Missing": missing_count,
        "Valid Values": valid_count, "Missing Rate (%)": round(missing_rate, 1),
    })

# Dashboard metrics
show_section("PORTFOLIO SNAPSHOT", "Claims overview")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total claims", f"{total:,}")
m2.metric("Needs data review", f"{review_count:,}", delta=f"{review_count / total * 100:.1f}% of total" if total else None)
m3.metric("High risk", f"{high_count:,}")
m4.metric("Risk calculated", f"{calculated_count:,}")

m5, m6, m7, m8 = st.columns(4)
m5.metric("Medium risk", f"{medium_count:,}")
m6.metric("No document flags", f"{clear_count:,}")
m7.metric("Duplicate-ID rows", f"{int(duplicate_ids.sum()):,}")
m8.metric("Invalid-document rows", f"{int(invalid_document_rows.sum()):,}")

st.caption(f"Source: {uploaded_file.name}  •  {datetime.now().strftime('%d %b %Y, %I:%M %p')}  •  High-risk share of calculated claims: {high_pct:.1f}%")
st.divider()

tab_overview, tab_docs, tab_trends, tab_records, tab_exports, tab_ai = st.tabs([
    "📊 Risk overview", "📄 Document analytics", "📈 Trends & amounts",
    "🔎 Claim explorer", "⬇️ Export centre", "🤖 AI Review"
])

with tab_overview:
    show_section("REVIEW PRIORITY", "Risk and data-quality distribution")
    left, right = st.columns([1.1, 1])
    risk_order = ["HIGH", "MEDIUM", "NO DOCUMENT FLAGS", "NOT CALCULATED"]
    risk_counts = df["Risk Level"].value_counts().reindex(risk_order, fill_value=0).rename_axis("Risk Level").reset_index(name="Claims")
    with left:
        fig = px.bar(risk_counts, x="Risk Level", y="Claims", color="Risk Level",
                     color_discrete_map={"HIGH": "#dc2626", "MEDIUM": "#f59e0b",
                                         "NO DOCUMENT FLAGS": "#0f766e", "NOT CALCULATED": "#64748b"})
        fig.update_layout(showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
                          margin=dict(l=10, r=10, t=20, b=10), xaxis_title="", yaxis_title="Claims")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        status_counts = df["Data Status"].value_counts().rename_axis("Data Status").reset_index(name="Rows")
        fig2 = px.pie(status_counts, names="Data Status", values="Rows", hole=.62,
                      color="Data Status", color_discrete_map={"VALID": "#0f766e", "REVIEW REQUIRED": "#f59e0b"})
        fig2.update_layout(legend_title_text="", margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig2, use_container_width=True)
    st.markdown("#### Risk summary")
    st.dataframe(risk_counts, use_container_width=True, hide_index=True)

with tab_docs:
    show_section("DOCUMENT COMPLETENESS", "Availability by required document")
    doc_df = pd.DataFrame(doc_stats)
    left, right = st.columns(2)
    with left:
        fig = px.bar(doc_df, x="Document", y="Missing", color="Document",
                     color_discrete_sequence=["#2563eb", "#0f766e", "#f59e0b"])
        fig.update_layout(showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
                          margin=dict(l=10, r=10, t=20, b=10), xaxis_title="", yaxis_title="Missing documents")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig = px.bar(doc_df, x="Document", y="Missing Rate (%)", color="Document",
                     color_discrete_sequence=["#2563eb", "#0f766e", "#f59e0b"])
        fig.update_layout(showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
                          margin=dict(l=10, r=10, t=20, b=10), xaxis_title="", yaxis_title="Missing rate (%)")
        st.plotly_chart(fig, use_container_width=True)
    st.dataframe(doc_df, use_container_width=True, hide_index=True)

with tab_trends:
    show_section("TIME & VALUE", "Claim trends and financial exposure")
    date_col = find_column(df.columns, DATE_CANDIDATES)
    amount_col = find_column(df.columns, AMOUNT_CANDIDATES)
    if date_col:
        dates = pd.to_datetime(df[date_col], errors="coerce")
        dated = pd.DataFrame({"Parsed Date": dates}).dropna()
        if not dated.empty:
            dated["Month"] = dated["Parsed Date"].dt.to_period("M").astype(str)
            monthly = dated.groupby("Month").size().reset_index(name="Claims")
            fig = px.line(monthly, x="Month", y="Claims", markers=True)
            fig.update_traces(line=dict(color="#2563eb", width=3), marker=dict(size=7))
            fig.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                              margin=dict(l=10, r=10, t=20, b=10), xaxis_title="", yaxis_title="Claims")
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"Date column used: {date_col}")
        else:
            st.info(f"No valid dates were found in '{date_col}'.")
    else:
        st.info("Add a date column (for example, Claim Date or Admission Date) to enable monthly trends.")
    st.divider()
    if amount_col:
        amounts = pd.to_numeric(df[amount_col].astype(str).str.replace(",", "", regex=False).str.replace("₹", "", regex=False).str.strip(), errors="coerce")
        valid_amounts = amounts.dropna()
        if not valid_amounts.empty:
            a1, a2, a3 = st.columns(3)
            a1.metric("Total claim amount", f"₹{valid_amounts.sum():,.2f}")
            a2.metric("Average claim amount", f"₹{valid_amounts.mean():,.2f}")
            a3.metric("Largest claim amount", f"₹{valid_amounts.max():,.2f}")
            amount_plot = pd.DataFrame({"Claim ID": df.loc[amounts.notna(), "Claim ID"].astype(str), "Amount": amounts[amounts.notna()].values})
            fig = px.bar(amount_plot.head(50), x="Claim ID", y="Amount")
            fig.update_traces(marker_color="#2563eb")
            fig.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                              margin=dict(l=10, r=10, t=20, b=10), xaxis_title="Claim ID", yaxis_title="Amount")
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Amount chart displays up to the first 50 rows with valid numeric amounts.")
        else:
            st.info("The amount column exists, but it has no valid numeric values.")
    else:
        st.info("Add Claim Amount, Bill Amount, Total Amount or Amount to enable amount analytics.")

with tab_records:
    show_section("SEARCH & FILTER", "Explore claim-level records")
    f1, f2, f3 = st.columns([1.2, 1, 1])
    with f1:
        search_text = st.text_input("Search Claim ID", placeholder="e.g. CLM-1001")
    with f2:
        selected_risks = st.multiselect("Risk level", risk_order, default=risk_order)
    with f3:
        selected_status = st.multiselect("Data status", ["VALID", "REVIEW REQUIRED"],
                                         default=["VALID", "REVIEW REQUIRED"])
    filtered = df.copy()
    if search_text.strip():
        filtered = filtered[filtered["Claim ID"].astype(str).str.contains(search_text.strip(), case=False, na=False)]
    filtered = filtered[filtered["Risk Level"].isin(selected_risks) & filtered["Data Status"].isin(selected_status)]
    st.caption(f"Showing {len(filtered):,} of {len(df):,} records")
    display_columns = ["Claim ID"] + REQUIRED_DOCS + ["Risk Level", "Missing Documents", "Data Status"]
    st.dataframe(filtered[display_columns], use_container_width=True, hide_index=True)
    st.download_button("⬇️ Download filtered results (CSV)",
                       filtered.to_csv(index=False).encode("utf-8-sig"),
                       file_name="claimguard_filtered_results.csv", mime="text/csv",
                       use_container_width=False)

with tab_exports:
    show_section("REPORTING", "Download analysis outputs")
    st.markdown("Export the reviewed data for follow-up, or generate a PDF summary for a project demonstration.")
    e1, e2 = st.columns(2)
    with e1:
        st.markdown("#### All review results")
        st.caption("Includes normalized document values, risk flags and data-quality status.")
            # ClaimGuard AI | Consistency Review
    with st.expander("🧠 Consistency Review — Check individual claims", expanded=False):
        if filtered.empty:
            st.info("No claims match the selected filters.")
        else:
            selected_index = st.selectbox(
                "Select a claim to review",
                options=filtered.index.tolist(),
                format_func=lambda idx: str(filtered.loc[idx, "Claim ID"]),
                key="consistency_claim_selector",
            )

            selected_row = filtered.loc[selected_index]
            findings = run_claim_consistency_checks(selected_row)

            st.caption(
                "Rule-based checks only. Findings require verification by authorized staff."
            )
            st.dataframe(
                pd.DataFrame(findings),
                use_container_width=True,
                hide_index=True,
            )
        st.download_button("Download all results (CSV)", df.to_csv(index=False).encode("utf-8-sig"),
                           file_name="claimguard_all_results.csv", mime="text/csv", use_container_width=True)
        issues = df[df["Data Status"] == "REVIEW REQUIRED"]
        st.download_button("Download data-quality issues (CSV)", issues.to_csv(index=False).encode("utf-8-sig"),
                           file_name="claimguard_data_quality_issues.csv", mime="text/csv", use_container_width=True)
    with e2:
        st.markdown("#### Professional PDF report")
        st.caption("Executive metrics, document availability, claim-level review and important limitations.")
        metrics = {"total": total, "review": review_count, "high": high_count,
                   "medium": medium_count, "clear": clear_count,
                   "calculated": calculated_count, "high_pct": high_pct}
        try:
            pdf_bytes = make_pdf(df, doc_stats, metrics, uploaded_file.name)
            st.download_button("Download PDF report", data=pdf_bytes,
                               file_name="ClaimGuard_AI_Claims_Report.pdf",
                               mime="application/pdf", use_container_width=True)
        except Exception as error:
            st.error(f"Could not generate the PDF report: {error}")


with tab_ai:
    show_section("AI-ASSISTED REVIEW", "ClaimGuard AI Review Assistant")
    st.markdown(
        "Generate an explanatory summary of the existing rule-based results. "
        "AI output is advisory only and must be checked by authorized staff."
    )
    st.warning(
        "Privacy: use synthetic test data only. Before continuing, confirm that you "
        "understand the limited review information below will be sent to OpenAI."
    )
    ai_consent = st.checkbox(
        "I confirm this is synthetic/demo data and consent to sending the limited review information to OpenAI.",
        key="claimguard_ai_consent",
    )

    ai_summary_clicked = st.button(
        "Generate AI portfolio summary",
        disabled=not ai_consent,
        key="claimguard_ai_summary_button",
    )
    if ai_summary_clicked:
        try:
            api_key = st.secrets.get("OPENAI_API_KEY", "")
            if not api_key:
                st.error(
                    "OPENAI_API_KEY is missing. Add it in Streamlit app settings → Secrets."
                )
            else:
                # Only aggregate metrics are sent for this summary; no claim rows or identifiers.
                summary_payload = {
                    "total_claims": int(total),
                    "needs_data_review": int(review_count),
                    "high_risk_document_flags": int(high_count),
                    "medium_risk_document_flags": int(medium_count),
                    "no_document_flags": int(clear_count),
                    "risk_calculated": int(calculated_count),
                    "high_risk_share_percent": round(float(high_pct), 1),
                    "document_statistics": doc_stats,
                }
                client = OpenAI(api_key=api_key)
                with st.spinner("Generating AI portfolio summary..."):
                    response = client.responses.create(
                        model="gpt-5.5",
                        store=False,
                        instructions=(
                            "You are a healthcare claims operations review assistant. "
                            "Explain only the supplied aggregate metrics. Do not claim fraud, "
                            "do not approve or reject claims, do not invent causes or facts. "
                            "Give a concise executive summary, key review priorities, and "
                            "practical data-quality follow-up steps. State that a human must verify."
                        ),
                        input=str(summary_payload),
                    )
                st.markdown("### AI portfolio summary")
                st.markdown(response.output_text)
        except Exception as error:
            st.error(
                "The AI summary could not be generated. Check that the API key is valid, "
                "API billing/credits are active, and the selected model is available. "
                f"Technical detail: {error}"
            )

    st.divider()
    st.markdown("### Explain one claim")
    if filtered.empty:
        st.info("No claims match the filters in Claim Explorer.")
    else:
        ai_claim_index = st.selectbox(
            "Choose a claim",
            options=filtered.index.tolist(),
            format_func=lambda idx: str(filtered.loc[idx, "Claim ID"]),
            key="claimguard_ai_claim_selector",
        )
        ai_row = filtered.loc[ai_claim_index]
        ai_findings = run_claim_consistency_checks(ai_row)
        ai_claim_clicked = st.button(
            "Generate AI explanation",
            disabled=not ai_consent,
            key="claimguard_ai_claim_button",
        )
        if ai_claim_clicked:
            try:
                api_key = st.secrets.get("OPENAI_API_KEY", "")
                if not api_key:
                    st.error(
                        "OPENAI_API_KEY is missing. Add it in Streamlit app settings → Secrets."
                    )
                else:
                    # Do not send the claim ID, patient identifiers, dates, or free-text fields.
                    limited_claim = {
                        "rule_based_risk_level": str(ai_row.get("Risk Level", "")),
                        "data_status": str(ai_row.get("Data Status", "")),
                        "missing_documents": str(ai_row.get("Missing Documents", "")),
                        "required_document_flags": {
                            doc: ("missing" if ai_row.get(doc) is False else
                                  "received" if ai_row.get(doc) is True else "invalid/unknown")
                            for doc in REQUIRED_DOCS
                        },
                        "consistency_findings": [
                            {
                                "check": str(item.get("Check", "")),
                                "finding": str(item.get("Finding", "")),
                                "severity": str(item.get("Severity", "")),
                            }
                            for item in ai_findings
                        ],
                    }
                    client = OpenAI(api_key=api_key)
                    with st.spinner("Generating AI claim explanation..."):
                        response = client.responses.create(
                            model="gpt-5.5",
                            store=False,
                            instructions=(
                                "You are a healthcare claims operations review assistant. "
                                "Explain the provided rule-based flags in plain, professional language. "
                                "Separate observed flags from recommendations. Do not infer fraud, "
                                "medical necessity, or claim validity. Never approve or reject a claim. "
                                "Suggest practical documents/checks for a human reviewer and state "
                                "that the result is advisory, not a final decision."
                            ),
                            input=str(limited_claim),
                        )
                    st.markdown("### AI claim explanation")
                    st.markdown(response.output_text)
            except Exception as error:
                st.error(
                    "The AI explanation could not be generated. Check that the API key is valid, "
                    "API billing/credits are active, and the selected model is available. "
                    f"Technical detail: {error}"
                )
    st.caption(
        "AI outputs are explanations of supplied review flags, not fraud detection or claim adjudication. "
        "Final decisions remain with authorized healthcare staff."
    )

with st.expander("Data-quality details"):
    q1, q2, q3 = st.columns(3)
    q1.metric("Blank Claim IDs", int(blank_ids.sum()))
    q2.metric("Duplicate-ID rows", int(duplicate_ids.sum()))
    q3.metric("Rows with invalid documents", int(invalid_document_rows.sum()))
    if blank_ids.any():
        st.warning(f"Blank Claim IDs found: {int(blank_ids.sum())}")
    if duplicate_ids.any():
        st.warning(f"Duplicate-ID rows found: {int(duplicate_ids.sum())}")
        st.dataframe(raw_df.loc[duplicate_ids, ["Claim ID"]], use_container_width=True, hide_index=True)
    for col in REQUIRED_DOCS:
        bad = invalid_masks[col]
        if bad.any():
            st.warning(f"{col}: {int(bad.sum())} invalid or missing value(s). Examples: {raw_df.loc[bad, col].astype(str).unique().tolist()[:10]}")
    if not review_mask.any():
        st.success("No blank IDs, duplicate IDs or invalid document values detected.")

st.divider()
st.markdown(
    '<div class="small-note">ClaimGuard AI is a portfolio demonstration. Rules flag missing documentation for manual review only; they do not establish fraud or make claim approval/rejection decisions. Final decisions belong to authorized healthcare staff. Use synthetic data only.</div>',
    unsafe_allow_html=True,
)


