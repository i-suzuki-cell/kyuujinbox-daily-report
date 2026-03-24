@echo off
cd /d C:\Users\k-tan\Documents\kyujinbox
"C:\Users\k-tan\AppData\Local\Programs\Python\Python313\python.exe" -m streamlit run dashboard.py --server.headless true --server.port 8501 --server.address 0.0.0.0
