#!/usr/bin/env python3
"""
Theo dõi bài đăng mới trên nhiều trang tuyển sinh sau đại học (UMP, PNT).

Cài đặt:  pip install requests beautifulsoup4
Chạy 1 lần (dùng với cron / GitHub Actions):  python ump_watch.py
Chạy lặp mỗi 15 phút:                          python ump_watch.py --loop 900

Gửi email qua biến môi trường: SMTP_USER, SMTP_PASS, MAIL_TO
(tuỳ chọn: SMTP_HOST, SMTP_PORT - mặc định Gmail)
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
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Thêm trang mới: chỉ cần thêm 1 mục vào danh sách này.
SITES = [
    {
        "key": "ump",
        "label": "UMP",
        "url": "https://ump.edu.vn/tuyen-sinh-dao-tao/sau-dai-hoc/tuyen-sinh",
        "item": "ul.bl-list-notification > li",
        "link": "h4 a",
        "date": ".txt-date",
    },
    {
        "key": "pnt",
        "label": "PNT",
        "url": "https://psdh.pnt.edu.vn/vi/tuyen-sinh-sau-dai-hoc",
        "item": "section.topic-content .widget",
        "link": "a.txt-title",
        "date": ".txt-date",
    },
]

STATE_FILE = Path(__file__).with_name("ump_seen.json")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Accept-Language": "vi,en;q=0.8",
}


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def fetch_posts(site: dict) -> list[dict]:
    r = requests.get(site["url"], headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    posts = []
    for item in soup.select(site["item"]):
        a = item.select_one(site["link"])
        if not a or not a.get("href"):
            continue
        date = item.select_one(site["date"])
        posts.append({
            "url": urljoin(site["url"], a["href"].strip()),
            "title": clean(a.get_text()),
            "date": clean(date.get_text()) if date else "",
        })
    return posts


def load_state() -> dict:
    """Trả về {site_key: {url: post}}. Tự chuyển đổi file cũ (chỉ có UMP)."""
    if not STATE_FILE.exists():
        return {}
    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    known_keys = {s["key"] for s in SITES}
    if data and not (set(data) <= known_keys):  # định dạng cũ: {url: post}
        data = {"ump": data}
    return data


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                          encoding="utf-8")


def send_email(subject: str, body: str) -> None:
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


def notify(site: dict, post: dict) -> None:
    label = site["label"]
    msg = f"[{label}] Bài mới ({post['date']}): {post['title']}\n{post['url']}"
    print(msg, flush=True)
    send_email(f"[{label}] {post['title']}", msg)


def check_site(site: dict, state: dict) -> bool:
    """Trả về True nếu state thay đổi."""
    posts = fetch_posts(site)
    if not posts:
        print(f"[{site['label']}] Không đọc được bài nào - "
              "có thể cấu trúc trang đã đổi.", file=sys.stderr)
        return False

    seen = state.get(site["key"])
    if seen is None:  # lần đầu với trang này: chỉ lưu mốc
        state[site["key"]] = {p["url"]: p for p in posts}
        print(f"[{site['label']}] Lần đầu: đã lưu {len(posts)} bài làm mốc.")
        return True

    new_posts = [p for p in posts if p["url"] not in seen]
    for p in reversed(new_posts):  # báo từ cũ đến mới
        notify(site, p)
        seen[p["url"]] = p
    if not new_posts:
        print(f"{time.strftime('%H:%M:%S')} [{site['label']}] chưa có bài mới.")
    return bool(new_posts)


def check_once() -> None:
    state = load_state()
    changed = False
    for site in SITES:
        try:  # lỗi ở 1 trang không làm hỏng trang còn lại
            changed |= check_site(site, state)
        except Exception as e:
            print(f"[{site['label']}] Lỗi: {e}", file=sys.stderr)
    if changed:
        save_state(state)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", type=int, default=0,
                    help="Chạy lặp, số giây giữa các lần kiểm tra (0 = chạy 1 lần)")
    args = ap.parse_args()

    if not args.loop:
        check_once()
        return
    while True:
        check_once()
        time.sleep(args.loop)


if __name__ == "__main__":
    main()
