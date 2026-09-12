# Mini Pharma Shipment Risk Analyzer

Run locally with Streamlit. From the project directory, create a virtualenv, install dependencies, then run:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Upload your Excel file and the app will show: total shipments, high-risk count, temperature excursions, top-5 highest-risk rows, a risk distribution chart, and short recommendations.
