# Pipeline: make ingest -> make labels -> make documents -> make features. `make backtest` comes with the model.
PY ?= python3

ingest:
	$(PY) -m src.ingest.edgar_fsds
	$(PY) -c "import pandas as pd; s=pd.read_csv('data/interim/fsds_sub.csv.gz',dtype={'cik':str}); c=s[s.sic.isin([7370,7371,7372,7373]) & s.form.isin(['10-K','10-KT','10-Q','10-K/A','10-Q/A'])].cik.unique(); pd.Series(sorted(c),name='cik').to_csv('data/interim/candidate_ciks.csv',index=False)"
	$(PY) -c "import pandas as pd; from src.ingest import edgar_companyconcept as cc; cc.main_float(pd.read_csv('data/interim/candidate_ciks.csv',dtype=str).cik.tolist())"
	$(PY) -c "from src.universe.universe import load_10k_table, ever_eligible; ever_eligible(load_10k_table()).to_csv('data/interim/ever_eligible.csv',index=False)"
	$(PY) -c "import pandas as pd; from src.ingest import edgar_submissions; edgar_submissions.main(pd.read_csv('data/interim/ever_eligible.csv',dtype=str).cik.tolist())"

labels:
	$(PY) -c "import pandas as pd; from src.labels.build_events import build; build(pd.read_csv('data/interim/ever_eligible.csv',dtype=str).cik.tolist())"
	$(PY) -m src.labels.report

documents:
	$(PY) -m src.ingest.edgar_documents
	$(PY) -c "import pandas as pd; from src.ingest import edgar_companyconcept as cc; cc.main_concepts(pd.read_csv('data/interim/ever_eligible.csv',dtype=str).cik.tolist())"
	$(PY) -c "import pandas as pd; from src.ingest.edgar_fsds import extract_facts; extract_facts(pd.read_csv('data/interim/ever_eligible.csv',dtype=str).cik.tolist())"

features:
	$(PY) -m src.features.panel
	$(PY) -m src.features.quality_report

.PHONY: ingest labels documents features
