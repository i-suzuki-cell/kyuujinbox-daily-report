from pathlib import Path

# URLs
LOGIN_URL = "https://secure.kyujinbox.com/login"
AD_REPORT_URL = "https://saiyo.kyujinbox.com/ad"

# 広告レポート画面の固定パラメータ
AD_REPORT_PARAMS = {
    "g": "5",
    "cf": "",
    "ici": "1",
    "cc": "",
    "kn": "",
    "haf": "",
    "hif": "",
    "hdf": "",
    "ps": "2",
    "s": "",
    "st": "2",
    "pg": "",
    "li": "",
    "dl": "",
}

# パス
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
ACCOUNTS_FILE = BASE_DIR / "accounts.json"

# Playwright設定
HEADLESS = False  # テスト時はブラウザを表示する
TIMEOUT_MS = 30000
