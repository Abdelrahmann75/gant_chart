#!/bin/bash

# Exit on any error
set -e

# Upgrade pip safely
pip install --upgrade pip

# Install requirements (you can use relative path here if you're in /home/site/wwwroot)
pip install -r requirements.txt

# Run the Streamlit app
python -m streamlit run IPR_APP.py --server.port 8000 --server.enableCORS false
