#!/usr/bin/env python3
"""食べログから各店舗の営業時間を取得し data/shop-hours.json に保存する。

使い方:
  python scripts/fetch_tabelog_hours.py              # 全店（Tabelog URL 有り）
  python scripts/fetch_tabelog_hours.py --priority   # 百名店・TRY・ミシュランのみ
  python scripts/fetch_tabelog_hours.py --resume     # 未取得分だけ再実行

保存フォーマット (data/shop-hours.json):
  {
    "https://tabelog.com/.../13XXXXXX": {
      "shop": "店名",
      "Mon": ["11:30-15:00", "17:30-21:00"],  # 営業セッション
      "Tue": ["11:30-15:00", "17:30-21:00"],
      "Wed": [],   # 定休（確定）
      "Thu": null, # 未確認
      ...
      "src": "tabelog",
      "as_of": "2026-05-30"
    }
  }
"""
from __future__ import annotations
import argparse
import html as htmlmod
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
HOURS_FILE = os.path.join(DATA, "shop-hours.json")
RAMEN_FILE = os.path.join(DATA, "ramen.json")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
TODAY = str(date.today())
DELAY = 0.8  # seconds between requests

DAYS_JP = ["月", "火", "水", "木", "金", "土", "日"]
DAY_EN = {"月": "Mon", "火": "Tue", "水": "Wed", "木": "Thu", "金": "Fri", "土": "Sat", "日": "Sun"}
ALL_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ---------------------------------------------------------------------------
# HTML fetch
# ---------------------------------------------------------------------------

def fetch_html(url: str) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ja"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print(f"  [rate-limit] sleeping 30s …", flush=True)
            time.sleep(30)
            return fetch_html(url)
        print(f"  [HTTP {e.code}] {url}", flush=True)
        return None
    except Exception as e:
        print(f"  [error] {e}", flush=True)
        return None


# ---------------------------------------------------------------------------
# Hours parser
# ---------------------------------------------------------------------------

def _norm_time(t: str) -> str:
    m = re.match(r"(\d{1,2}):(\d{2})", t)
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else t


def _expand_day_range(s: str) -> list[str]:
    """「月～土」「月・水」などを ['月','火',...] に展開。"""
    s = s.strip()
    m = re.match(r"([月火水木金土日])[～〜~]([月火水木金土日])", s)
    if m:
        si = DAYS_JP.index(m.group(1))
        ei = DAYS_JP.index(m.group(2))
        return DAYS_JP[si: ei + 1] if ei >= si else DAYS_JP[si:] + DAYS_JP[: ei + 1]
    result = [c for c in re.split(r"[・、\s]+", s) if c in DAYS_JP]
    return result if result else ([s] if s in DAYS_JP else [])


def parse_hours_text(text: str) -> dict[str, list[str] | None]:
    """食べログの営業時間テキストを曜日→セッションリストの辞書に変換する。

    セッションリスト:
      ["11:30-15:00", "17:30-21:00"]  : その日の営業時間
      []                               : 定休日確定
      null (key absence)               : 未確認
    """
    result: dict[str, list[str] | None] = {}

    # --- 形式1: [月] ヘッダースタイル ------------------------------------------
    if "[月]" in text or "[火]" in text or "[水]" in text:
        current_day: str | None = None
        sessions: list[str] = []
        for raw in text.split("\n"):
            line = raw.strip()
            m = re.match(r"\[([月火水木金土日])\]", line)
            if m:
                if current_day and current_day in DAY_EN:
                    result[DAY_EN[current_day]] = sessions
                current_day, sessions = m.group(1), []
                continue
            if not current_day or not line:
                continue
            if "定休日" in line or line == "休":
                sessions = []
                continue
            m2 = re.match(r"(\d{1,2}:\d{2})\s*[-~～〜]\s*(\d{1,2}:\d{2})", line)
            if m2:
                sessions.append(f"{_norm_time(m2.group(1))}-{_norm_time(m2.group(2))}")
        if current_day and current_day in DAY_EN:
            result[DAY_EN[current_day]] = sessions
        return result

    # --- 形式2: 「月〜土 HH:MM〜HH:MM」スタイル ---------------------------------
    closed_days: set[str] = set()

    # 定休日セクションの解析
    for pat in (r"■定休日\n([^\n■]+)", r"定休日[：:]\s*([^\n]+)", r"定休日\s+([月火水木金土日・〜～、\s祝]+)"):
        cm = re.search(pat, text)
        if cm:
            for part in re.split(r"[・、\s]+", cm.group(1)):
                if not part or part in ("祝", "祝日"):
                    continue
                for d in _expand_day_range(part):
                    if d in DAY_EN:
                        closed_days.add(DAY_EN[d])
            break

    # 営業時間セッションの解析 (L.O. を除去してから処理)
    open_sessions: dict[str, list[str]] = {}
    clean = re.sub(r"\(L\.O[^)]*\)", "", text)
    for line in clean.split("\n"):
        line = line.strip()
        m = re.match(
            r"([月火水木金土日・〜～〜~\-\s]+?)\s+"
            r"(\d{1,2}:\d{2})\s*[-~～〜]\s*(\d{1,2}:\d{2})", line
        )
        if m:
            t1, t2 = _norm_time(m.group(2)), _norm_time(m.group(3))
            for d in _expand_day_range(m.group(1)):
                if d in DAY_EN:
                    en = DAY_EN[d]
                    open_sessions.setdefault(en, []).append(f"{t1}-{t2}")

    for en in ALL_EN:
        if en in closed_days:
            result[en] = []
        elif en in open_sessions:
            result[en] = open_sessions[en]
    return result


def extract_hours_from_html(html: str) -> dict[str, list[str] | None] | None:
    """HTML から JSON-LD FAQPage を探して営業時間を抽出する。"""
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL):
        try:
            d = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if d.get("@type") != "FAQPage":
            continue
        for q in d.get("mainEntity", []):
            if "営業時間" not in q.get("name", ""):
                continue
            raw = q.get("acceptedAnswer", {}).get("text", "")
            text = htmlmod.unescape(re.sub("<[^>]+>", "", raw))
            parsed = parse_hours_text(text)
            if parsed:
                return parsed
    return None


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def load_master() -> dict:
    if os.path.exists(HOURS_FILE):
        with open(HOURS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_master(master: dict) -> None:
    with open(HOURS_FILE, "w", encoding="utf-8") as f:
        json.dump(master, f, ensure_ascii=False, indent=2)


def run(urls_shops: list[tuple[str, str]], resume: bool) -> None:
    master = load_master()
    todo = [(u, n) for u, n in urls_shops if not resume or u not in master]
    print(f"取得対象: {len(todo)} 店 / 全 {len(urls_shops)} 店", flush=True)

    for i, (url, shop) in enumerate(todo, 1):
        if url in master and resume:
            continue
        print(f"[{i}/{len(todo)}] {shop} … ", end="", flush=True)
        html = fetch_html(url)
        if html is None:
            print("SKIP (fetch error)", flush=True)
            time.sleep(DELAY)
            continue
        parsed = extract_hours_from_html(html)
        if parsed:
            master[url] = {"shop": shop, **parsed, "src": "tabelog", "as_of": TODAY}
            print("OK", flush=True)
        else:
            print("no hours data", flush=True)
        if i % 20 == 0:
            save_master(master)
        time.sleep(DELAY)

    save_master(master)
    print(f"\n完了 — {HOURS_FILE} に {len(master)} 件を保存", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--priority", action="store_true", help="百名店・TRY・ミシュラン優先")
    ap.add_argument("--resume", action="store_true", help="未取得分のみ実行")
    args = ap.parse_args()

    with open(RAMEN_FILE, encoding="utf-8") as f:
        data = json.load(f)

    tabelog_shops = [
        (r["source_url"], r["shop"])
        for r in data
        if r.get("source_url") and "tabelog.com" in r["source_url"]
        and not r["source_url"].endswith("rank/")
        and not r["source_url"].endswith("rank")
        and not r["source_url"].endswith("rstLst/")
        and not r["source_url"].endswith("rstLst")
        and "/R" not in r["source_url"]
    ]

    if args.priority:
        priority_set = set()
        for r in data:
            t = r.get("feature", "") + " " + " ".join(a for a in (r.get("awards") or []))
            if (r.get("try_awards") or r.get("awards")):
                priority_set.add(r.get("source_url"))
        tabelog_shops = [(u, n) for u, n in tabelog_shops if u in priority_set]

    run(tabelog_shops, resume=args.resume)


if __name__ == "__main__":
    main()
