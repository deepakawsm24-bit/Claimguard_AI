ClaimGuard AI — Professional Healthcare Claims Analytics
A Streamlit portfolio demo for claims document completeness, data-quality checks, risk-flag summaries, claim trends, and CSV/PDF exports.
Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```
Deploy on Streamlit Community Cloud
Upload `app.py` and `requirements.txt` to the root of your GitHub repository.
Open Streamlit Community Cloud and create/select the app.
Set the main file path to `app.py`.
Deploy and review the app logs if dependency installation fails.
Required columns
`Claim ID`
`Discharge Summary`
`Final Bill`
`Investigation Reports`
Document values can be Yes/No, True/False, 1/0, Received/Not Received, Present/Absent, or Available/Missing.
Optional columns include `Claim Date`, `Admission Date`, `Discharge Date`, `Submission Date`, `Claim Amount`, `Bill Amount`, `Total Amount`, or `Amount`.
Important limitation
This is a rule-based demonstration. Risk flags indicate missing documentation for manual review; they do not establish fraud or make claim approval/rejection decisions. Use synthetic test data only, never real patient records.
