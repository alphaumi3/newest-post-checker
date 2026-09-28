#!/usr/bin/env python3
"""
Theo dõi bài đăng mới tại:
https://ump.edu.vn/tuyen-sinh-dao-tao/sau-dai-hoc/tuyen-sinh

Cài đặt:  pip install requests beautifulsoup4
Chạy 1 lần (dùng với cron / Task Scheduler):  python ump_watch.py
Chạy lặp mỗi 10 phút:                          python ump_watch.py --loop 600

Tuỳ chọn: gửi thông báo qua Telegram bằng biến môi trường
  TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
"""
import argparse
import json
import os
import re
import smtplib
import sys
import time
from email.message import EmailMessage
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://ump.edu.vn/tuyen-sinh-dao-tao/sau-dai-hoc/tuyen-sinh"
STATE_FILE = Path(__file__).with_name("ump_seen.json")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Accept-Language": "vi,en;q=0.8",
}


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def fetch_posts() -> list[dict]:
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    posts = []
    for li in soup.select("ul.bl-list-notification > li"):
        a = li.select_one("h4 a")
        if not a or not a.get("href"):
            continue
        date = li.select_one(".txt-date")
        posts.append({
            "url": a["href"].strip(),
            "title": clean(a.get_text()),
            "date": clean(date.get_text()) if date else "",
        })
    return posts


def load_seen() -> dict | None:
    if not STATE_FILE.exists():
        return None
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save_seen(seen: dict) -> None:
    STATE_FILE.write_text(json.dumps(seen, ensure_ascii=False, indent=2),
                          encoding="utf-8")


def send_email(subject: str, body: str) -> None:
    """Gửi mail qua SMTP. Cần: SMTP_USER, SMTP_PASS, MAIL_TO
    (tuỳ chọn: SMTP_HOST, SMTP_PORT - mặc định Gmail)."""
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    to = os.getenv("MAIL_TO", user)
    if not (user and password and to):
        return
    m = EmailMessage()
    m["Subject"] = subject
    m["From"] = user
    m["To"] = to
    m.set_content(body)
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "465"))
    try:
        with smtplib.SMTP_SSL(host, port, timeout=30) as s:
            s.login(user, password)
            s.send_message(m)
    except Exception as e:
        print(f"Gửi email lỗi: {e}", file=sys.stderr)


def notify(post: dict) -> None:
    msg = f"[UMP] Bài mới ({post['date']}): {post['title']}\n{post['url']}"
    print(msg, flush=True)
    send_email(f"[UMP] {post['title']}", msg)
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={"chat_id": chat_id, "text": msg},
                timeout=15,
            )
        except requests.RequestException as e:
            print(f"Gửi Telegram lỗi: {e}", file=sys.stderr)


def check_once() -> None:
    posts = fetch_posts()
    if not posts:
        print("Không đọc được bài nào - có thể cấu trúc trang đã đổi.",
              file=sys.stderr)
        return

    seen = load_seen()
    if seen is None:
        # Lần chạy đầu: chỉ lưu mốc, không báo
        save_seen({p["url"]: p for p in posts})
        print(f"Lần đầu: đã lưu {len(posts)} bài làm mốc.")
        return

    new_posts = [p for p in posts if p["url"] not in seen]
    # Báo từ cũ đến mới
    for p in reversed(new_posts):
        notify(p)
        seen[p["url"]] = p
    if new_posts:
        save_seen(seen)
    else:
        print(f"{time.strftime('%H:%M:%S')} - chưa có bài mới.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", type=int, default=0,
                    help="Chạy lặp, số giây giữa các lần kiểm tra (0 = chạy 1 lần)")
    args = ap.parse_args()

    if not args.loop:
        check_once()
        return
    while True:
        try:
            check_once()
        except Exception as e:  # không để vòng lặp chết vì lỗi mạng
            print(f"Lỗi: {e}", file=sys.stderr)
        time.sleep(args.loop)


if __name__ == "__main__":
    main()
