
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="ClaimGuard AI",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 ClaimGuard AI")
st.subheader("Healthcare Claim Document Checking & Risk Review")
st.info(
    "Demo project: This tool checks document availability "
    "and flags claims for manual review. It does not approve or reject claims."
)

st.sidebar.header("Claim Details")
claim_id = st.sidebar.text_input("Claim ID", value="CG001")

st.sidebar.write("### Documents Received")
discharge_summary = st.sidebar.checkbox("Discharge Summary")
final_bill = st.sidebar.checkbox("Final Bill")
investigation_reports = st.sidebar.checkbox("Investigation Reports")

if st.sidebar.button("Check Claim", type="primary"):
    missing = []

    if not discharge_summary:
        missing.append("Discharge Summary")
    if not final_bill:
        missing.append("Final Bill")
    if not investigation_reports:
        missing.append("Investigation Reports")

    st.header("Claim Review Result")
    st.write("**Claim ID:**", claim_id)

    if len(missing) >= 2:
        risk = "HIGH"
    elif len(missing) == 1:
        risk = "MEDIUM"
    else:
        risk = "NO DOCUMENT FLAGS"

    if risk == "HIGH":
        st.error("Risk Level: HIGH")
    elif risk == "MEDIUM":
        st.warning("Risk Level: MEDIUM")
    else:
        st.success("Risk Level: NO DOCUMENT FLAGS")

    if missing:
        st.write("**Missing documents:**")
        for document in missing:
            st.write("- ", document)
        st.warning("Recommended action: Manual verification required.")
    else:
        st.success("All required documents are marked as received.")
        st.write("Recommended action: Continue with the normal review process.")

    st.caption(
        "This is a rule-based demo. Final claim decisions must be made "
        "by authorized healthcare staff."
    )

st.divider()
st.subheader("How to Use")
st.write(
    "1. Enter a Claim ID in the sidebar. "
    "2. Tick the documents received. "
    "3. Click Check Claim to see the review result."
)

st.caption("Demo only — do not enter real patient details.")
