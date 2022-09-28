#!/bin/bash
python -m spacy download fr_core_news_sm
nginx -t &&
service nginx start &&
streamlit run project_contents/app/app.py --theme.base "dark"