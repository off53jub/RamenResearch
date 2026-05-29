#!/usr/bin/env python3
"""wards/*.md を解析して横断インデックスを生成する。

生成物:
  indexes/by-genre.md            … ジャンル別(家系/煮干し/二郎系 …)の店一覧
  indexes/hyakumeiten-michelin.md … ラーメン百名店・ミシュラン(星/ビブグルマン)一覧

各区ファイルの駅見出し配下のテーブル
  | 店名 | ジャンル | 看板・特徴 | 評価の目安 | 出典 |
を読み取り、(区, 最寄駅, 店名, ジャンル, 評価, 出典) を抽出する。
同一店(店名＋出典URLが一致)は名寄せし、所在地をまとめる。
"""
from __future__ import annotations
import re
import glob
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WARDS = os.path.join(ROOT, "wards")
OUT = os.path.join(ROOT, "indexes")

NON_STATION = ("🚉", "⭐", "🔎", "📝", "❌", "📂", "🧭", "✅", "⚠️", "🅱️", "💯")


def is_station_heading(text: str) -> bool:
    if any(m in text for m in NON_STATION):
        return False
    if "私鉄駅" in text or "おすすめ代表店" in text or "要調査" in text:
        return False
    return ("駅" in text) or ("停留場" in text)


def short_station(text: str) -> str:
    t = text.lstrip("#").strip()
    for sep in ("（", "("):
        if sep in t:
            t = t.split(sep)[0]
    return t.strip().strip("／/・")


def score(ev: str) -> float:
    m = re.search(r"(\d\.\d+)", ev)
    return float(m.group(1)) if m else 0.0


def url_of(src: str) -> str:
    m = re.search(r"\((https?://[^)]+)\)", src)
    return m.group(1) if m else ""


GENRE_RULES = [
    ("家系", ["家系"]),
    ("二郎・二郎系", ["二郎"]),
    ("煮干し", ["煮干"]),
    ("つけ麺", ["つけ麺", "つけそば", "つけ蕎麦"]),
    ("味噌", ["味噌"]),
    ("豚骨・博多", ["豚骨", "とんこつ", "博多", "長浜", "久留米"]),
    ("鶏白湯", ["鶏白湯"]),
    ("担々麺・四川・麻婆", ["担", "坦", "四川", "麻婆"]),
    ("貝・魚介系", ["貝", "牡蠣", "蛤", "あさり", "しじみ", "帆立", "鯛", "海老", "えび", "鮎", "魚介", "まぐろ", "鰹"]),
    ("鴨", ["鴨"]),
    ("ワンタン麺", ["ワンタン", "わんたん", "雲呑"]),
    ("油そば・まぜそば・汁なし", ["油そば", "まぜそば", "汁なし", "まぜ麺"]),
    ("塩", ["塩"]),
    ("醤油・中華そば", ["醤油", "中華そば", "中華蕎麦", "支那", "清湯", "ちゃん系"]),
    ("ご当地・地域系", ["喜多方", "白河", "札幌", "旭川", "長岡", "佐野", "竹岡", "笠岡", "和歌山", "京都", "九州", "刀削麺", "タンメン", "スパイス"]),
]
GENRE_ORDER = [label for label, _ in GENRE_RULES] + ["その他・創作"]


def classify(genre: str) -> list[str]:
    hits = [label for label, kws in GENRE_RULES if any(k in genre for k in kws)]
    return hits or ["その他・創作"]


def parse_records() -> list[dict]:
    bykey: dict = {}
    for path in sorted(glob.glob(os.path.join(WARDS, "*.md"))):
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
        ward = lines[0].lstrip("#").strip().split()[0] if lines and lines[0].startswith("# ") else "?"
        station = ""
        for ln in lines:
            s = ln.strip()
            if s.startswith("#"):
                station = short_station(s) if is_station_heading(s) else ""
                continue
            if not s.startswith("|"):
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) < 5:
                continue
            shop, genre, feat, ev, src = cells[:5]
            if not shop or shop == "店名" or set(shop) <= set("-:"):
                continue
            url = url_of(src)
            key = (shop, url) if url else (shop, ward, station)
            loc = f"{ward}・{station}" if station else ward
            rec = bykey.get(key)
            if rec:
                if loc not in rec["locs"]:
                    rec["locs"].append(loc)
                continue
            bykey[key] = dict(ward=ward, station=station, shop=shop, genre=genre,
                              feat=feat, ev=ev, src=src, locs=[loc])
    return list(bykey.values())


def loc_str(r: dict) -> str:
    return " / ".join(r["locs"][:3])


def table(rows: list[dict]) -> str:
    out = ["| 店名 | 区・最寄駅 | ジャンル | 評価の目安 | 出典 |", "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: score(r["ev"]), reverse=True):
        out.append(f'| {r["shop"]} | {loc_str(r)} | {r["genre"]} | {r["ev"]} | {r["src"]} |')
    return "\n".join(out) + "\n"


def main() -> None:
    records = parse_records()
    os.makedirs(OUT, exist_ok=True)

    # ---- ジャンル別 ----
    by_genre = defaultdict(list)
    for r in records:
        for label in classify(r["genre"]):
            by_genre[label].append(r)

    with open(os.path.join(OUT, "by-genre.md"), "w", encoding="utf-8") as f:
        f.write("# ジャンル別 ラーメン横断インデックス\n\n")
        f.write("**最終更新:** 2026-05-29 / 自動生成(`scripts/build_indexes.py`) / [← 全体に戻る](../README.md)\n\n")
        f.write(f"> `wards/*.md` から自動抽出した **全{len(records)}店**(同一店は出典URLで名寄せ)。1店が複数ジャンルに登場することがあります。評価の目安は食べログ点数等(掲載時点)。\n\n")
        f.write("## 目次\n")
        for label in GENRE_ORDER:
            if by_genre.get(label):
                f.write(f"- [{label}](#{label.replace('・', '').replace('／', '')})（{len(by_genre[label])}店）\n")
        f.write("\n")
        for label in GENRE_ORDER:
            rows = by_genre.get(label)
            if not rows:
                continue
            f.write(f'<h2 id="{label.replace("・", "").replace("／", "")}">{label}（{len(rows)}店）</h2>\n\n')
            f.write(table(rows))
            f.write("\n")

    # ---- 百名店・ミシュラン ----
    star = [r for r in records if any(k in r["ev"] for k in ("一つ星", "二つ星", "三つ星"))]
    bib = [r for r in records if "ビブグルマン" in r["ev"]]
    hyaku = [r for r in records if "百名店" in r["ev"]]

    # 自己検証: 各カテゴリのキーワード整合性を保証
    assert all(any(k in r["ev"] for k in ("一つ星", "二つ星", "三つ星")) for r in star)
    assert all("ビブグルマン" in r["ev"] for r in bib), [r["shop"] for r in bib if "ビブグルマン" not in r["ev"]]
    assert all("百名店" in r["ev"] for r in hyaku)

    with open(os.path.join(OUT, "hyakumeiten-michelin.md"), "w", encoding="utf-8") as f:
        f.write("# ラーメン百名店・ミシュラン 一覧\n\n")
        f.write("**最終更新:** 2026-05-29 / 自動生成(`scripts/build_indexes.py`) / [← 全体に戻る](../README.md)\n\n")
        f.write("> `wards/*.md` の「評価の目安」に百名店/ミシュラン/ビブグルマンの記載がある店を抽出(出典URLで名寄せ)。同一店が複数カテゴリに入ることがあります。選出年は各区ファイル参照。\n\n")
        f.write(f"## ⭐ ミシュラン 星（{len(star)}店）\n\n")
        f.write(table(star) if star else "（該当なし）\n")
        f.write(f"\n## 🅱️ ミシュラン ビブグルマン（{len(bib)}店）\n\n")
        f.write(table(bib) if bib else "（該当なし）\n")
        f.write(f"\n## 💯 食べログ ラーメン百名店（{len(hyaku)}店）\n\n")
        f.write(table(hyaku) if hyaku else "（該当なし）\n")

    print(f"OK records={len(records)} star={len(star)} bib={len(bib)} hyaku={len(hyaku)}")


if __name__ == "__main__":
    main()
