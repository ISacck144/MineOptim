.PHONY: install demo v0 v1 v2 test clean dashboard gif

install:
	pip install -r requirements.txt

demo: v0

v0:
	PYTHONPATH=src python -m experiments.run_ab --version v0

v1:
	PYTHONPATH=src python -m experiments.run_ab --version v1

v2:
	PYTHONPATH=src python -m experiments.run_ab --version v2

v0-andina:
	PYTHONPATH=src python -m experiments.run_ab --version v0 --config mina_andina

dashboard:
	PYTHONPATH=src streamlit run dashboard/app.py

gif:
	PYTHONPATH=src python experiments/render_gif.py

test:
	PYTHONPATH=src python -m pytest tests/ -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	find . -name "*.png" -path "*/results/*" -delete
