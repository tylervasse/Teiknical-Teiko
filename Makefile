.PHONY: setup pipeline dashboard

setup:
	@echo ">>> Installing Python dependencies..."
	pip install -r files/requirements.txt
	@echo ">>> Setup complete."

pipeline:
	@echo ">>> Building database..."
	python files/db_creation.py
	@echo ">>> Generating outputs..."
	python pipeline.py
	@echo ">>> Pipeline complete."

dashboard:
	@echo ">>> Starting Streamlit dashboard..."
	streamlit run files/streamlit_dashboard.py --server.enableCORS false --server.enableXsrfProtection false
