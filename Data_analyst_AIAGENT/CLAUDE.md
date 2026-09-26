Data Analyst AI Agent
Role
Act as a Senior AI Agent + Data Analytics Engineer. Build a production-style Data Analyst AI Agent using Python, LangGraph and Streamlit. Write clean, modular, executable code and automatically fix errors found during testing.
Stack
Python 3.11+
Streamlit — local deployment
LangGraph — agent workflow/state
Pandas, NumPy, Scikit-learn
Plotly — interactive dashboards
OpenPyXL — Excel
LLM: open-source model via Groq Cloud
ReportLab — PDF reports
SQLite — metadata/traces
OpenTelemetry + Prometheus + Grafana — observability
Langfuse — LLM/agent traceability
Pytest — testing
Use .env for API keys. Never hard-code secrets.
Required Workflow
Problem Statement
→ KPI Input
→ CSV/XLSX Upload
→ Data Quality Analysis
→ Cleaning Plan
→ Clean Data
→ User Question
→ Analysis
→ Dashboard
→ Insights
→ PDF Report
→ Email Draft
→ Observability & Traceability
1. Problem Statement
Ask user to enter the business problem.
2. KPI
Ask user to define relevant KPIs.
Store Problem Statement + KPIs in LangGraph state.
3. Data Upload
Support CSV and XLSX.
Show dataset preview, rows, columns and data types.
4. Data Quality Agent
Automatically detect:
Missing values
Duplicate rows
Outliers
Data types
Numerical/categorical columns
Unique values
Invalid/inconsistent values
Constant columns
Basic descriptive statistics
Display a professional Data Quality Report with issue counts and percentages.
5. Data Cleaning Agent
Create a deterministic cleaning plan based on best practices.
Handle:
Missing values
Duplicates
Outliers
Incorrect types
Categorical inconsistencies
Invalid values
IMPORTANT:
The LLM should recommend/coordinate cleaning, but Pandas/validated Python functions must perform transformations.
Never silently delete important data.
Keep original dataset unchanged.
Maintain a complete cleaning audit trail.
Show:
Before Cleaning → Actions → After Cleaning.
Allow clean dataset download.
6. Data Analyst Agent
Provide chat interface for questions about cleaned data.
Example:
"Show regional sales vs target."
Agent should:
Understand question → identify KPI → plan analysis → execute Python/Pandas → validate result → generate visualization → explain result.
Never fabricate numbers. All numerical claims must come from executed analysis.
Memory (two tiers):
Short-term: `conversation_history` on the LangGraph state (`graph/state.py`). Holds the current session's chat turns in-process only. The last `SHORT_TERM_MEMORY_TURNS` turns (`config/settings.py`, default 6) are injected into the analyst prompt as `CONVERSATION_HISTORY` so follow-up questions ("what about that region?", "vs last time?") resolve correctly. Used only to disambiguate references — never a source of numbers.
Long-term: `services/memory_service.py`, SQLite-backed (`data/db/memory.sqlite`), keyed by `session_id`. Persists every validated turn across app restarts and is browsable/resumable via the Memory tab, independent of the in-process short-term buffer.
7. Dashboard Agent
Generate interactive Plotly visualizations based on user questions.
Use appropriate charts automatically:
Bar, Line, Scatter, Pie/Donut, Histogram, Box Plot, KPI Cards, Tables.
Dashboard must remain grounded in cleaned data.
8. Insight Agent
Generate:
Key findings
KPI performance
Trends
Anomalies
Business implications
Data-supported recommendations
Clearly separate facts from recommendations.
9. PDF Report
Generate downloadable professional PDF containing:
Problem Statement
→ KPIs
→ Data Quality Summary
→ Cleaning Summary
→ Analysis
→ Dashboard/Charts
→ Key Insights
→ Recommendations
10. Email Generator
Generate a professional email summarizing:
analysis + important KPIs + insights + recommended actions.
Provide editable email preview.
11. LangGraph Architecture
Use nodes:
START
→ Problem/KPI
→ Data Ingestion
→ Quality Agent
→ Cleaning Agent
→ Analyst Agent
→ Visualization Agent
→ Insight Agent
→ Report Agent
→ Email Agent
→ END
Create conditional edges for errors, validation failures and re-analysis.
Maintain shared LangGraph state containing:
problem_statement,
kpis,
raw_data,
clean_data,
quality_report,
cleaning_log,
user_question,
analysis_result,
charts,
insights,
report_path,
email,
errors,
trace_id.
12. Guardrails
No fabricated data or insights
Never execute arbitrary user Python
Validate uploaded files
Limit file size
Sanitize filenames
Preserve raw data
Log every transformation
Validate analysis before presenting results
Handle missing/invalid inputs gracefully
Never expose API keys
Require user confirmation for potentially destructive cleaning decisions
13. Observability
Instrument workflow with OpenTelemetry.
Track:
Agent/node latency
Total request latency
LLM calls
Token usage when available
Tool/function calls
Errors
Successful/failed executions
Expose metrics to Prometheus and visualize in Grafana.
14. Traceability
Use Langfuse + application audit logs.
For every analysis maintain:
Trace ID
→ Timestamp
→ User Question
→ Agent/Node
→ LLM Call
→ Tool Call
→ Input
→ Output
→ Data transformation
→ Latency
→ Error/Status
Add Streamlit Observability & Traceability page showing the current run trace.
UI/UX
Build premium professional Streamlit UI with a light theme.
Top animated/moving headline:
DATA ANALYST AI AGENT — From Raw Data to Decision Intelligence
Use:
Large readable fonts
Light background
KPI cards
Clean spacing
Sidebar workflow/navigation
Progress indicators
Interactive Plotly charts
Minimal clutter
Responsive layout
Pages/Tabs:
Business Context
Data Upload
Data Quality
Data Cleaning
Ask Your Data
Dashboard
Insights
PDF Report
Email
Observability & Traceability
Project Structure
app.py
agents/
graph/
tools/
services/
observability/
reports/
tests/
data/
config/
CLAUDE.md
.env.example
requirements.txt
README.md
Keep files modular and avoid unnecessary complexity.
Development Rules
First create architecture and file structure.
Implement one workflow stage at a time.
Use reusable functions and typed state.
Add exception handling.
Add structured logging.
Add unit/integration tests.
Run tests after implementation.
Fix errors before completion.
Test with synthetic CSV/XLSX data.
Ensure streamlit run app.py starts successfully.
Definition of Done
The project is complete only when this flow works end-to-end:
Problem → KPI → Upload → Quality Report → Cleaning → Question → Analysis → Dashboard → Insights → PDF → Email → Observability/Traceability
The application must run locally without broken imports, placeholder core functionality, fabricated analysis, or unresolved errors.
