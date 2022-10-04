#!/bin/bash
nginx -t &&
service nginx start &&
streamlit run project_contents/app/app.py --server.maxUploadSize 20000