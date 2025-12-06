
# AI Dataset Quality Analyzer

A lightweight H2O Wave web app for analyzing dataset quality and generating AI-powered insights and fix suggestions.

**Key features**
- Upload CSV / Excel files and inspect dataset overview (rows, columns, memory, missing values, duplicates).
- Rule-based data quality checks (missing values, duplicates, outliers, type issues, class imbalance, high-correlation, constant columns).
- AI-generated: concise executive summary, technical insights, and per-issue fix suggestions (uses Google Generative AI / Gemini).
- Visualizations: distribution plots, correlation heatmap, column quality table, and summary gauges.

**Repository layout**
- `app.py` — Wave app entrypoint and UI flow (upload -> analysis -> results -> issue details).
- `utils/`
	- `data_loader.py` — file loading and dataset metadata helpers.
	- `analyzer.py` — deterministic data quality checks (class `DataAnalyzer`).
	- `visualizer.py` — Wave-friendly UI card builders and plotting helpers.
	- `ai_engine.py` — AI integration: builds prompts and calls Google Generative AI SDK (Gemini).
- `requirements.txt` — Python dependencies (ensure installed in the venv Wave uses).
- `uploads/` — uploaded files are saved here at runtime.

**High-level workflow (what happens after you submit a CSV)**
1. User uploads file via the `Upload Your Dataset` card.
2. `app.py` saves the file (`q.site.download`) and calls `utils.load_dataset()` to parse it into a `pandas.DataFrame`.
3. The DataFrame is stored on `q.client.df` and `get_dataset_info()` / `get_column_stats()` are used to populate UI summary cards.
4. When the user clicks `Start AI Analysis`, `DataAnalyzer.analyze()` runs rule-based checks and returns a `quality_score` and a list of `issues`.
5. The app calls `AIEngine.generate_insights()` and `AIEngine.generate_executive_summary()` to get AI text outputs and displays them.
6. For a specific issue, clicking `View Details & Fixes` opens details and calls `AIEngine.suggest_fixes()` to generate targeted recommendations.

**Setup (Windows / PowerShell)**
1. Create and activate a Python venv (recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Set the required environment variables (PowerShell):

```powershell
$env:GOOGLE_API_KEY = 'YOUR_API_KEY'
# optional: specify model name
$env:GOOGLE_MODEL = 'models/gemini-2.5-flash'
```

4. Run the app (in the same shell where env vars are set):

```powershell
wave run app.py
```

Then open the Wave URL the server prints (usually http://localhost:10101).

**AI integration notes & troubleshooting**
- The app's AI integration uses `google.generativeai` (Gemini). The exact SDK API surface varies between releases — if you see errors like `module 'google.generativeai' has no attribute 'generate'` or other attribute errors:
	- Confirm the package is installed in the same virtual environment that runs Wave:
		```powershell
		.\.venv\Scripts\Activate
		pip show google-generativeai requests
		```
	- Run a quick model-listing smoke test to confirm SDK + key work:
		```powershell
		python - <<'PY'
import google.generativeai as genai, os
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
print([m.name for m in genai.list_models()])
PY
		```
	- If the SDK entrypoints differ, update `utils/ai_engine.py` to add a compatibility wrapper or a REST fallback. The app expects `AIEngine` to expose:
		- `generate_insights(df, issues)`
		- `suggest_fixes(issue, df_sample)`
		- `generate_executive_summary(quality_score, issues, df_info)`
- If AI calls fail, the app shows a friendly message and continues to display rule-based results.

**Common errors & fixes**
- File load errors: malformed CSVs or very large files may cause `pandas` to raise exceptions — open the file in a Python REPL and try `pd.read_csv()` to see full trace.
- Event/UX issues: if clicking `View Details & Fixes` does nothing, restart Wave so `app.py` changes are loaded; the app maps dynamic button names to a normalized `q.args.view_issue` value.
- Environment mismatch: ensure Wave is started from the same shell where the venv is activated and `GOOGLE_API_KEY` is defined.

**Development notes**
- To adjust rule thresholds or add checks edit `utils/analyzer.py` (class `DataAnalyzer`).
- To change prompt wording or model usage, edit `utils/ai_engine.py` (prompt builders `_build_insight_prompt`, `_build_fix_prompt`, `_build_summary_prompt`).
- Visual presentation is in `utils/visualizer.py` — change plot/card layouts there.

**Contributing**
- Open an issue or submit a PR. Keep changes focused (one concern per PR) and include brief testing steps.

**License**
--

---


