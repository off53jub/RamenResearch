#!/usr/bin/env python3
"""regions/<都県>/*.md を解析して横断インデックス・データ出力を生成する。

生成物:
  indexes/by-genre.md             … ジャンル別の店一覧
  indexes/hyakumeiten-michelin.md … 百名店・ミシュラン(星/ビブグルマン)
  indexes/practical.md            … 実用インデックス(深夜/朝・予約/行列・殿堂3.7+・区別TOP)
  indexes/lineage.md              … 系譜マップ(出身店・のれん分け・系列)
  data/ramen.csv / data/ramen.json … 全店の構造化データ

各区ファイルの駅見出し配下のテーブル
  | 店名 | ジャンル | 看板・特徴 | 評価の目安 | 出典 |
を読み取り、(区, 最寄駅, 店名, ジャンル, 特徴, 評価, 出典) を抽出する。
同一店(店名＋出典URL)は名寄せし、所在地をまとめる。
"""
from __future__ import annotations
import re
import csv
import json
import glob
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGIONS = os.path.join(ROOT, "regions")
OUT = os.path.join(ROOT, "indexes")
DATA = os.path.join(ROOT, "data")
DOCS = os.path.join(ROOT, "docs")
UPDATED = "2026-05-29"

# 地域ディレクトリ → 表示名(出力順)。多摩は東京都だが23区と区別するため別ラベル。
PREFS = [
    ("tokyo", "東京都"),
    ("tokyo-tama", "東京都(多摩)"),
    ("kanagawa", "神奈川県"),
    ("saitama", "埼玉県"),
    ("chiba", "千葉県"),
]
PREF_LABEL = dict(PREFS)

NON_STATION = ("🚉", "⭐", "🔎", "📝", "❌", "📂", "🧭", "✅", "⚠️", "🅱️", "💯", "🍜", "🗺️")


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


def extract_lines(heading: str) -> list[str]:
    """Extract railway line names from station heading parentheticals.
    e.g. '八王子駅（JR中央・横浜・八高線）／ 京王八王子駅（京王線）' → ['JR中央・横浜・八高線', '京王線']
    """
    parts = re.findall(r'[（(]([^)）\n]+)[）)]', heading)
    result = []
    for part in parts:
        for seg in re.split(r'\s*/\s*|／', part):
            seg = seg.strip()
            if seg:
                result.append(seg)
    return result


def parse_closed_days(feat: str) -> list[str]:
    """Parse closed weekdays from feature text. Returns English day abbreviations.
    Handles: 月休, 月火休, 土日祝休, 月曜休, 月曜日休, etc.
    """
    DAY_MAP = {"月": "Mon", "火": "Tue", "水": "Wed", "木": "Thu",
               "金": "Fri", "土": "Sat", "日": "Sun"}
    if "無休" in feat:
        return []
    # Normalise "X曜日?" → "X" so 月曜休/月曜日休 is treated same as 月休
    text = re.sub(r'([月火水木金土日])曜日?', r'\1', feat)
    result = set()
    for m in re.finditer(r'([月火水木金土日]+(?:祝)?)休', text):
        for c in m.group(1):
            if c in DAY_MAP:
                result.add(DAY_MAP[c])
    ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return sorted(result, key=lambda d: ORDER.index(d))


def score(ev: str) -> float:
    m = re.search(r"(\d\.\d+)", ev)
    return float(m.group(1)) if m else 0.0


def url_of(src: str) -> str:
    m = re.search(r"\((https?://[^)]+)\)", src)
    if not m:
        return ""
    u = m.group(1)
    # tabelog の言語別URL(/en/)や末尾スラッシュ差で同一店が二重登録されるのを防ぐ
    u = u.replace("tabelog.com/en/", "tabelog.com/").rstrip("/")
    return u


# ---- ジャンル分類 ----
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


# ---- 系譜マップ: 親(本店/系統) → 検出キーワード ----
# 各レコードの「特徴」テキストにキーワードがあれば、その系統のメンバーとする。
LINEAGE = [
    ("ラーメン二郎・二郎インスパイア", ["二郎"]),
    ("家系（横浜家系・武蔵家系統 ほか）", ["家系", "武蔵家", "王道家", "武道家"]),
    ("「一燈」グループ・系譜", ["一燈"]),
    ("「たんたん亭」系", ["たんたん亭"]),
    ("「ほん田」出身・系列", ["ほん田"]),
    ("「かづ屋」出身", ["かづ屋"]),
    ("「七彩」出身", ["七彩"]),
    ("「麺壁九年」系列", ["麺壁九年"]),
    ("「井の庄」系", ["井の庄"]),
    ("「和渦」グループ", ["和渦"]),
    ("「春木屋」出身", ["春木屋"]),
    ("一風堂 出身", ["一風堂"]),
    ("札幌「すみれ」出身・純すみ系", ["すみれ", "純すみ"]),
    ("「はやし田」系列", ["はやし田"]),
    ("「大勝軒」系（東池袋ほか）", ["大勝軒"]),
    ("中目黒「Jazzy Beats」出身", ["Jazzy Beats", "ジャジー"]),
    ("「竹末」系", ["竹末"]),
    ("「富士丸」系（二郎系）", ["富士丸"]),
]


def parse_records() -> list[dict]:
    bykey: dict = {}
    for slug, pref in PREFS:
        for path in sorted(glob.glob(os.path.join(REGIONS, slug, "*.md"))):
            with open(path, encoding="utf-8") as f:
                lines = f.read().splitlines()
            ward = lines[0].lstrip("#").strip().split()[0] if lines and lines[0].startswith("# ") else "?"
            station = ""
            current_lines: list[str] = []
            for ln in lines:
                s = ln.strip()
                if s.startswith("#"):
                    if is_station_heading(s):
                        station = short_station(s)
                        current_lines = extract_lines(s)
                    else:
                        station = ""
                        current_lines = []
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
                key = (shop, url) if url else (shop, pref, ward, station)
                loc = f"{ward}・{station}" if station else ward
                rec = bykey.get(key)
                if rec:
                    if loc not in rec["locs"]:
                        rec["locs"].append(loc)
                    for rline in current_lines:
                        if rline not in rec["lines"]:
                            rec["lines"].append(rline)
                    continue
                bykey[key] = dict(pref=pref, ward=ward, station=station, shop=shop,
                                  genre=genre, feat=feat, ev=ev, src=src, url=url, locs=[loc],
                                  lines=list(current_lines),
                                  closed_days=parse_closed_days(feat))
    return list(bykey.values())


def tag(r: dict) -> str:
    """認定・特徴の判定に使う結合テキスト(評価＋特徴)。"""
    return r["ev"] + " " + r["feat"]


def awards_of(r: dict) -> list[str]:
    t = tag(r)
    a = []
    if any(k in t for k in ("一つ星", "二つ星", "三つ星")):
        a.append("ミシュラン星")
    if "ビブグルマン" in t:
        a.append("ビブグルマン")
    if "百名店" in t:
        a.append("百名店")
    return a


def loc_str(r: dict) -> str:
    # 例: 「東京都 千代田区・秋葉原駅」。複数駅は最大3つまで。
    pref = r.get("pref", "")
    locs = " / ".join(r["locs"][:3])
    return f"{pref} {locs}".strip()


def table(rows: list[dict]) -> str:
    out = ["| 店名 | 都県・区市・最寄駅 | ジャンル | 評価の目安 | 出典 |", "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: score(r["ev"]), reverse=True):
        out.append(f'| {r["shop"]} | {loc_str(r)} | {r["genre"]} | {r["ev"]} | {r["src"]} |')
    return "\n".join(out) + "\n"


def header(title: str) -> str:
    return (f"# {title}\n\n"
            f"**最終更新:** {UPDATED} / 自動生成(`scripts/build_indexes.py`) / [← 全体に戻る](../README.md)\n\n")


def write_genre(records):
    by_genre = defaultdict(list)
    for r in records:
        for label in classify(r["genre"]):
            by_genre[label].append(r)
    with open(os.path.join(OUT, "by-genre.md"), "w", encoding="utf-8") as f:
        f.write(header("ジャンル別 ラーメン横断インデックス"))
        f.write(f"> `regions/**/*.md` から自動抽出した **全{len(records)}店**(同一店は出典URLで名寄せ)。1店が複数ジャンルに登場することがあります。評価の目安は食べログ点数等(掲載時点)。\n\n")
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
            f.write(table(rows) + "\n")
    return by_genre


def write_awards(records):
    star = [r for r in records if "ミシュラン星" in awards_of(r)]
    bib = [r for r in records if "ビブグルマン" in awards_of(r)]
    hyaku = [r for r in records if "百名店" in awards_of(r)]
    assert all("ミシュラン星" in awards_of(r) for r in star)
    assert all("ビブグルマン" in awards_of(r) for r in bib)
    assert all("百名店" in awards_of(r) for r in hyaku)
    with open(os.path.join(OUT, "hyakumeiten-michelin.md"), "w", encoding="utf-8") as f:
        f.write(header("ラーメン百名店・ミシュラン 一覧"))
        f.write("> `regions/**/*.md` の「評価の目安」「看板・特徴」に百名店/ミシュラン/ビブグルマンの記載がある店を抽出(出典URLで名寄せ)。同一店が複数カテゴリに入ることがあります。選出年は各区ファイル参照。\n\n")
        f.write(f"## ⭐ ミシュラン 星（{len(star)}店）\n\n")
        f.write(table(star) if star else "（該当なし）\n")
        f.write(f"\n## 🅱️ ミシュラン ビブグルマン（{len(bib)}店）\n\n")
        f.write(table(bib) if bib else "（該当なし）\n")
        f.write(f"\n## 💯 食べログ ラーメン百名店（{len(hyaku)}店）\n\n")
        f.write(table(hyaku) if hyaku else "（該当なし）\n")
    return star, bib, hyaku


def write_practical(records):
    late = [r for r in records if any(k in r["feat"] for k in ("深夜", "翌1", "翌2", "翌3", "翌4", "24時間", "〜24", "1時まで", "2時まで"))]
    morning = [r for r in records if any(k in r["feat"] for k in ("朝ラー", "朝6", "朝5", "朝7", "早朝", "朝営業", "6:30", "7:00から", "朝〜"))]
    reserve = [r for r in records if any(k in r["feat"] for k in ("予約", "整理券", "オンライン順番", "電子チケット"))]
    queue = [r for r in records if any(k in r["feat"] for k in ("行列", "連日行列", "売切", "売り切れ", "スープ切れ", "仕舞い", "終了"))]
    hall = [r for r in records if score(r["ev"]) >= 3.75]

    # 区・市別TOP3(食べログ点数が取れた店のみ)。都県→区/市でグループ化。
    bypw = defaultdict(lambda: defaultdict(list))
    for r in records:
        if score(r["ev"]) > 0:
            bypw[r["pref"]][r["ward"]].append(r)

    with open(os.path.join(OUT, "practical.md"), "w", encoding="utf-8") as f:
        f.write(header("実用インデックス（深夜・朝 / 予約・行列 / 殿堂 / 区市別TOP）"))
        f.write("> `regions/**/**.md` の「看板・特徴」「評価の目安」から自動抽出。深夜/朝・予約/行列はメモに該当語がある店のみ(網羅ではない)。点数は掲載時点の目安。\n\n")

        f.write(f"## 🌙 深夜まで営業（{len(late)}店）\n\n")
        f.write(table(late) if late else "（該当なし）\n")
        f.write(f"\n## 🌅 朝ラー・早朝営業（{len(morning)}店）\n\n")
        f.write(table(morning) if morning else "（該当なし）\n")
        f.write(f"\n## 📝 予約制・整理券（{len(reserve)}店）\n\n")
        f.write(table(reserve) if reserve else "（該当なし）\n")
        f.write(f"\n## 🚶 行列・売り切れ仕舞い（{len(queue)}店）\n\n")
        f.write(table(queue) if queue else "（該当なし）\n")
        f.write(f"\n## 🏆 殿堂（食べログ3.75以上 / {len(hall)}店）\n\n")
        f.write(table(hall) if hall else "（該当なし）\n")

        f.write("\n## 📍 区市別おすすめTOP3（食べログ点数順）\n\n")
        for _, pref in PREFS:
            if pref not in bypw:
                continue
            f.write(f"### {pref}\n\n")
            for w in sorted(bypw[pref], key=lambda w: -max(score(r["ev"]) for r in bypw[pref][w])):
                rows = sorted(bypw[pref][w], key=lambda r: score(r["ev"]), reverse=True)[:3]
                picks = "／".join(f'{r["shop"]}（{r["ev"].split("／")[0].replace("食べログ", "").replace("約", "").strip()}）' for r in rows)
                f.write(f"- **{w}**: {picks}\n")
            f.write("\n")
    return late, morning, reserve, queue, hall


def write_lineage(records):
    fams = []
    for name, kws in LINEAGE:
        members = [r for r in records if any(k in (r["feat"] + " " + r["shop"]) for k in kws)]
        # 二郎/家系はジャンル列にも強く出るので補完
        if name.startswith("ラーメン二郎"):
            members = [r for r in records if "二郎" in (r["feat"] + " " + r["genre"] + " " + r["shop"])]
        if name.startswith("家系"):
            members = [r for r in records if ("家系" in (r["feat"] + " " + r["genre"] + " " + r["shop"]))
                       or any(k in r["feat"] for k in ("武蔵家", "王道家", "武道家"))]
        # 重複除去
        uniq, seen = [], set()
        for r in sorted(members, key=lambda r: score(r["ev"]), reverse=True):
            k = (r["shop"], r["url"])
            if k in seen:
                continue
            seen.add(k)
            uniq.append(r)
        if uniq:
            fams.append((name, uniq))

    with open(os.path.join(OUT, "lineage.md"), "w", encoding="utf-8") as f:
        f.write(header("系譜マップ（出身店・のれん分け・系列）"))
        f.write("> `regions/**/*.md` の「看板・特徴」テキストから系統キーワードで自動抽出。**根拠**列にDB内の記述を併記しています(各店の正確な師弟・資本関係は出典先で確認のこと)。同一店が複数系統に現れることがあります。\n\n")
        f.write("## 目次\n")
        for name, uniq in fams:
            f.write(f"- {name}（{len(uniq)}店）\n")
        f.write("\n")
        for name, uniq in fams:
            f.write(f"### {name}（{len(uniq)}店）\n\n")
            f.write("| 店名 | 区・最寄駅 | 評価の目安 | 根拠（DB内の記述） | 出典 |\n|---|---|---|---|---|\n")
            for r in uniq:
                f.write(f'| {r["shop"]} | {loc_str(r)} | {r["ev"]} | {r["feat"]} | {r["src"]} |\n')
            f.write("\n")
    return fams


def write_data(records):
    os.makedirs(DATA, exist_ok=True)
    os.makedirs(os.path.join(DOCS, "data"), exist_ok=True)
    rows = sorted(records, key=lambda r: (-score(r["ev"]), r["pref"], r["ward"]))
    cols = ["shop", "pref", "ward", "stations", "genre", "genres", "tabelog_score",
            "awards", "feature", "source_url", "closed_days", "lines"]
    with open(os.path.join(DATA, "ramen.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r["shop"], r["pref"], r["ward"], " / ".join(r["locs"]), r["genre"],
                        "/".join(classify(r["genre"])), score(r["ev"]) or "",
                        ";".join(awards_of(r)), r["feat"], r["url"],
                        ";".join(r.get("closed_days", [])),
                        " / ".join(r.get("lines", []))])
    arr = [dict(shop=r["shop"], pref=r["pref"], ward=r["ward"], stations=r["locs"], genre=r["genre"],
               genres=classify(r["genre"]), tabelog_score=(score(r["ev"]) or None),
               awards=awards_of(r), feature=r["feat"], source_url=r["url"],
               closed_days=r.get("closed_days", []),
               lines=r.get("lines", [])) for r in rows]
    payload = json.dumps(arr, ensure_ascii=False, indent=2)
    with open(os.path.join(DATA, "ramen.json"), "w", encoding="utf-8") as f:
        f.write(payload)
    # GitHub Pages のビューア(docs/index.html)から相対参照するため docs/data にも複製
    with open(os.path.join(DOCS, "data", "ramen.json"), "w", encoding="utf-8") as f:
        f.write(payload)
    return len(rows)


def main() -> None:
    records = parse_records()
    os.makedirs(OUT, exist_ok=True)
    by_genre = write_genre(records)
    star, bib, hyaku = write_awards(records)
    late, morning, reserve, queue, hall = write_practical(records)
    fams = write_lineage(records)
    n = write_data(records)
    print(f"records={len(records)} csv/json={n}")
    print(f"awards: star={len(star)} bib={len(bib)} hyaku={len(hyaku)}")
    print(f"practical: late={len(late)} morning={len(morning)} reserve={len(reserve)} queue={len(queue)} hall={len(hall)}")
    print("lineage families:")
    for name, uniq in fams:
        print(f"  {name}: {len(uniq)}")


if __name__ == "__main__":
    main()
