# Flow-Analytics
使用python 動畫

## Local Setup
- Do not commit secrets or any real data files.
- Place your service account JSON at `data/private/service_account.json` (kept out of git).
- Share the target Google Sheet with the service account email you control.
- Install dependencies and run the smoke test:
  - `pip install -r requirements.txt`
  - `python scripts/gsheets_smoke_test.py`
