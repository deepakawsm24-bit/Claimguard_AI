# ClaimGuard AI — Healthcare Claims Intelligence

A healthcare claims analytics application designed to review claim data quality, monitor document completeness, prioritize claims for manual review, and generate professional PDF reports.

## Project Overview

ClaimGuard AI helps healthcare operations teams analyze claims data through an interactive dashboard. It highlights missing documents, identifies duplicate claim IDs and invalid document values, and summarizes claim review priorities.

This project is a **rule-based portfolio demonstration**, not a validated fraud-detection or automated claim-approval system.

## Key Features

- Interactive Streamlit dashboard
- Claims overview and risk distribution
- Document completeness analysis
- Claim-level review details
- Duplicate ID and data-quality checks
- Claim amount and trend analysis
- Filtered CSV exports
- Downloadable PDF summary reports

## Technology Stack

- Python
- Streamlit
- Pandas
- Plotly
- ReportLab
- CSV and Excel data processing

## How It Works

1. Upload a claims dataset in CSV or Excel format.
2. Validate required columns and claim data.
3. Review document availability and data-quality issues.
4. Explore claim summaries, risk categories, and trends.
5. Export filtered data or generate a PDF report.

## Example Results

In the sample dataset currently used for testing:

- Total claims: 5
- High-risk claims: 2
- Medium-risk claims: 1
- Claims without document flags: 2
- Duplicate-ID rows: 0
- Invalid-document rows: 0

These results are based on synthetic sample data and demonstrate the application's rule-based logic.

## Installation

Clone the repository:

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd Claimguard_AI
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
streamlit run app.py
```

## Important Limitations

Risk categories indicate potential missing-document or review requirements. They do not prove fraud and do not approve or reject claims. Final decisions must be made by authorized healthcare staff.

Use synthetic test data for demonstrations. Do not upload confidential patient or insurance information to a public application.

## Future Improvements

- Machine-learning-based risk prioritization
- Explainable risk indicators
- Expanded data validation
- Additional healthcare analytics and reporting

## Author

Healthcare Operations | Data Analytics | AI Research

Project: ClaimGuard AI
