#!/bin/bash
pip install --upgrade pip
pip install -r /home/site/wwwroot/requirements.txt
python -m streamlit run IPR_APP.py --server.port 8000 --server.enableCORS false
