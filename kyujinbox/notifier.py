import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)

# SMTP設定 - 環境に合わせて変更してください
SMTP_HOST = "smtp.gmail.com"  # メールサーバー
SMTP_PORT = 587
SMTP_USER = ""  # 送信元メールアドレス
SMTP_PASSWORD = ""  # アプリパスワード
FROM_EMAIL = ""  # 送信元
TO_EMAIL = "i-suzuki@partage.jp"


def send_report_email(results: dict, period: str):
    """週次レポートの完了通知メールを送信する。"""
    success_count = len(results["success"])
    failed_count = len(results["failed"])
    total = success_count + failed_count

    subject = f"【求人ボックス】週次CSVダウンロード完了 ({period})"

    body = f"""求人ボックス 週次CSVダウンロードが完了しました。

対象期間: {period}
結果: {success_count}/{total} アカウント成功

--- 成功 ---
{chr(10).join(f'  ✓ {name}' for name in results['success'])}
"""

    if results["failed"]:
        body += f"""
--- 失敗 ---
{chr(10).join(f'  ✗ {name}' for name in results['failed'])}
"""

    body += f"""
ダッシュボード: http://localhost:8501
"""

    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP設定が未完了のため、メール通知をスキップしました")
        logger.info(f"通知内容:\n{body}")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = FROM_EMAIL
        msg["To"] = TO_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"通知メール送信完了: {TO_EMAIL}")
        return True

    except Exception as e:
        logger.error(f"メール送信エラー: {e}")
        return False
