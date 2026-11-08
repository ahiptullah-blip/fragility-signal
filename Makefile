# Labels pipeline (Prompt 3). `make backtest` will be added once a model exists.
PY ?= python3

ingest:
	$(PY) -m src.ingest.edgar_fsds
	$(PY) -c "import pandas as pd; s=pd.read_csv('data/interim/fsds_sub.csv.gz',dtype={'cik':str}); c=s[s.sic.isin([7370,7371,7372,7373]) & s.form.isin(['10-K','10-KT','10-Q','10-K/A','10-Q/A'])].cik.unique(); pd.Series(sorted(c),name='cik').to_csv('data/interim/candidate_ciks.csv',index=False)"
	$(PY) -c "import pandas as pd; from src.ingest import edgar_float; edgar_float.main(pd.read_csv('data/interim/candidate_ciks.csv',dtype=str).cik.tolist())"
	$(PY) -c "from src.universe.universe import load_10k_table, ever_eligible; ever_eligible(load_10k_table()).to_csv('data/interim/ever_eligible.csv',index=False)"
	$(PY) -c "import pandas as pd; from src.ingest import edgar_submissions; edgar_submissions.main(pd.read_csv('data/interim/ever_eligible.csv',dtype=str).cik.tolist())"

labels:
	$(PY) -c "import pandas as pd; from src.labels.build_events import build; build(pd.read_csv('data/interim/ever_eligible.csv',dtype=str).cik.tolist())"
	$(PY) -m src.labels.report

.PHONY: ingest labels
