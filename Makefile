.PHONY: setup pipeline dashboard

setup:
	@echo ">>> Installing Python dependencies..."
	pip install -r requirements.txt
	@echo ">>> Setup complete."

pipeline:
	@echo ">>> Building database..."
	python load_data.py
	@echo ">>> Generating outputs..."
	python pipeline.py
	@echo ">>> Pipeline complete."

dashboard:
	@echo ">>> Starting Streamlit dashboard..."
	streamlit run app/streamlit_dashboard.py --server.enableCORS false --server.enableXsrfProtection false
