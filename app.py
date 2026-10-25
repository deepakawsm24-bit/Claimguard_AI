
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="ClaimGuard AI Dashboard",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 ClaimGuard AI")
st.subheader("Healthcare Claims Risk Dashboard")

st.info(
    "Demo only: Synthetic claims are used for dashboard display. "
    "Risk flags support manual review, not claim approval."
)

# Demo data only
data = [
    {"Claim ID": "CG001", "Discharge Summary": True,  "Final Bill": False, "Investigation Reports": False},
    {"Claim ID": "CG002", "Discharge Summary": True,  "Final Bill": True,  "Investigation Reports": False},
    {"Claim ID": "CG003", "Discharge Summary": True,  "Final Bill": True,  "Investigation Reports": True},
    {"Claim ID": "CG004", "Discharge Summary": False, "Final Bill": False, "Investigation Reports": True},
    {"Claim ID": "CG005", "Discharge Summary": True,  "Final Bill": True,  "Investigation Reports": True},
]

df = pd.DataFrame(data)

def review_claim(row):
    missing = sum([
        not row["Discharge Summary"],
        not row["Final Bill"],
        not row["Investigation Reports"]
    ])
    if missing >= 2:
        return "HIGH"
    elif missing == 1:
        return "MEDIUM"
    return "NO DOCUMENT FLAGS"

df["Risk Level"] = df.apply(review_claim, axis=1)

# Dashboard metrics
total = len(df)
high = int((df["Risk Level"] == "HIGH").sum())
medium = int((df["Risk Level"] == "MEDIUM").sum())
clear = int((df["Risk Level"] == "NO DOCUMENT FLAGS").sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Claims", total)
c2.metric("High Risk", high)
c3.metric("Medium Risk", medium)
c4.metric("No Document Flags", clear)

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("📊 Claims by Risk Level")
    chart_data = df["Risk Level"].value_counts()
    st.bar_chart(chart_data)

with right:
    st.subheader("🔎 Search Claim")
    search_id = st.text_input("Enter Claim ID", placeholder="e.g. CG001")
    if search_id:
        result = df[df["Claim ID"].str.contains(search_id, case=False, na=False)]
        if not result.empty:
            st.dataframe(result, use_container_width=True, hide_index=True)
        else:
            st.warning("No matching demo claim found.")

st.divider()
st.subheader("📋 All Demo Claims")

risk_filter = st.selectbox(
    "Filter by Risk Level",
    ["ALL", "HIGH", "MEDIUM", "NO DOCUMENT FLAGS"]
)

view = df if risk_filter == "ALL" else df[df["Risk Level"] == risk_filter]
st.dataframe(view, use_container_width=True, hide_index=True)

st.caption(
    "Demo records only. Do not enter real patient information. "
    "Authorized staff must verify documents and make all final decisions."
)

st.subheader("🧾 Check a Claim")

with st.form("claim_checker"):
    claim_id = st.text_input("Claim ID", value="CG006")
    discharge = st.checkbox("Discharge Summary received")
    bill = st.checkbox("Final Bill received")
    reports = st.checkbox("Investigation Reports received")
    submitted = st.form_submit_button("Check Claim")

if submitted:
    missing_docs = []
    if not discharge:
        missing_docs.append("Discharge Summary")
    if not bill:
        missing_docs.append("Final Bill")
    if not reports:
        missing_docs.append("Investigation Reports")

    if len(missing_docs) >= 2:
        st.error("Risk Level: HIGH")
    elif len(missing_docs) == 1:
        st.warning("Risk Level: MEDIUM")
    else:
        st.success("Risk Level: NO DOCUMENT FLAGS")

    st.write("Claim ID:", claim_id)
    if missing_docs:
        st.write("Missing documents:", ", ".join(missing_docs))
        st.warning("Manual verification required.")
    else:
        st.success("All required documents are marked as received.")
