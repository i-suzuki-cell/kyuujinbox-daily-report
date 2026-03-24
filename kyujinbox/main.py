import json
import logging
import sys
from datetime import date, timedelta

from config import ACCOUNTS_FILE, DATA_DIR
from scraper import download_csv
from notifier import send_report_email
from notion_sync import sync_to_notion

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def get_yesterday(today: date | None = None) -> date:
    """前日の日付を返す。"""
    if today is None:
        today = date.today()
    return today - timedelta(days=1)


def load_accounts() -> list[dict]:
    """accounts.json を読み込む。"""
    if not ACCOUNTS_FILE.exists():
        logger.error(f"アカウントファイルが見つかりません: {ACCOUNTS_FILE}")
        logger.error("accounts.example.json をコピーして accounts.json を作成してください。")
        sys.exit(1)

    with open(ACCOUNTS_FILE, encoding="utf-8") as f:
        accounts = json.load(f)

    logger.info(f"{len(accounts)} アカウントを読み込みました")
    return accounts


def main():
    """メイン処理: 全アカウントの前日分CSVをダウンロードする。"""
    accounts = load_accounts()
    yesterday = get_yesterday()

    target_date = yesterday.strftime("%Y/%m/%d")
    save_dir = DATA_DIR / yesterday.isoformat()  # data/2026-03-22/

    logger.info(f"対象日: {target_date}")
    logger.info(f"保存先: {save_dir}")

    results = {"success": [], "failed": []}

    for account in accounts:
        label = account["label"]
        # from と to を同じ日付にする（1日分）
        csv_path = download_csv(account, target_date, target_date, save_dir)
        if csv_path:
            results["success"].append(label)
        else:
            results["failed"].append(label)

    # 結果サマリー
    logger.info("=" * 50)
    logger.info(f"完了: {len(results['success'])}/{len(accounts)} アカウント")
    if results["success"]:
        logger.info(f"  成功: {', '.join(results['success'])}")
    if results["failed"]:
        logger.warning(f"  失敗: {', '.join(results['failed'])}")

    # Notion同期
    sync_to_notion(yesterday.isoformat(), yesterday.isoformat())

    # メール通知
    period = target_date
    send_report_email(results, period)


if __name__ == "__main__":
    main()
