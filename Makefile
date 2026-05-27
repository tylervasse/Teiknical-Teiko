.PHONY: setup pipeline dashboard

setup:
	@echo ">>> Installing Python dependencies..."
	pip install -r files/requirements.txt
	@echo ">>> Checking for Java (required by Nextflow)..."
	@which java > /dev/null 2>&1 || (sudo apt-get update -qq && sudo apt-get install -y -q default-jdk-headless && echo "Java installed.")
	@echo ">>> Checking for Nextflow..."
	@which nextflow > /dev/null 2>&1 || (curl -fsSL https://get.nextflow.io | bash && sudo mv nextflow /usr/local/bin/ && echo "Nextflow installed.")
	@echo ">>> Setup complete."

pipeline:
	@echo ">>> Running data pipeline with Nextflow..."
	nextflow run main.nf

dashboard:
	@echo ">>> Starting Streamlit dashboard..."
	streamlit run files/streamlit_dashboard.py --server.enableCORS false --server.enableXsrfProtection false
