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
UPDATED = "2026-05-30"

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


_LINE_HINTS = ("JR", "線", "ライン", "市営地下鉄", "メトロ", "みなとみらい",
               "京急", "東急", "相鉄", "京成", "小田急", "モノレール", "EX")


def is_station_heading(text: str) -> bool:
    if any(m in text for m in NON_STATION):
        return False
    if "私鉄駅" in text or "おすすめ代表店" in text or "要調査" in text:
        return False
    if ("駅" in text) or ("停留場" in text):
        return True
    # 「駅」字が省略されていても、括弧内に路線名があれば駅見出しとみなす
    # （横浜中心部の「関内（JR / 市営地下鉄）」「馬車道（みなとみらい線）」等）
    m = re.search(r"[（(]([^)）]+)[）)]", text)
    return bool(m and any(k in m.group(1) for k in _LINE_HINTS))


def short_station(text: str) -> str:
    t = text.lstrip("#").strip()
    for sep in ("（", "("):
        if sep in t:
            t = t.split(sep)[0]
    return t.strip().strip("／/・")


# ---- 路線タクソノミ（鉄道会社 → 路線）----
# 駅見出しの括弧内テキストから正準ラベルへマッピングする。
# 表記揺れ・圧縮形（例「JR中央・横浜・八高線」「有楽町・副都心線」）は
# expand_lines_text() で各路線名に展開してからキーワード照合する。
# 各要素: (鉄道会社, 正準ラベル, 照合キーワード)
TAXONOMY = [
    ("JR東日本", "JR山手線", ["山手線"]),
    ("JR東日本", "JR京浜東北線", ["京浜東北"]),
    ("JR東日本", "JR中央線", ["中央線", "中央本線", "中央快速"]),
    ("JR東日本", "JR総武線", ["総武線", "総武本線"]),
    ("JR東日本", "JR埼京線", ["埼京"]),
    ("JR東日本", "JR湘南新宿ライン", ["湘南新宿"]),
    ("JR東日本", "JR横須賀線", ["横須賀"]),
    ("JR東日本", "JR東海道線", ["東海道"]),
    ("JR東日本", "JR常磐線", ["常磐"]),
    ("JR東日本", "JR京葉線", ["京葉"]),
    ("JR東日本", "JR武蔵野線", ["武蔵野"]),
    ("JR東日本", "JR南武線", ["南武"]),
    ("JR東日本", "JR横浜線", ["横浜線"]),
    ("JR東日本", "JR根岸線", ["根岸"]),
    ("JR東日本", "JR八高線", ["八高"]),
    ("JR東日本", "JR川越線", ["川越線"]),
    ("JR東日本", "JR高崎線", ["高崎線"]),
    ("JR東日本", "JR宇都宮線", ["宇都宮線", "東北本線"]),
    ("JR東日本", "JR青梅線", ["青梅"]),
    ("JR東日本", "JR五日市線", ["五日市"]),
    ("JR東日本", "JR相模線", ["相模線"]),
    ("JR東日本", "JR鶴見線", ["鶴見線"]),
    ("JR東日本", "JR内房線", ["内房"]),
    ("JR東日本", "JR外房線", ["外房"]),
    ("JR東日本", "JR成田線", ["成田線"]),
    ("JR東日本", "JR久留里線", ["久留里"]),
    ("JR東日本", "JR各線（大ターミナル）", ["JR各線"]),
    ("東京メトロ", "銀座線", ["銀座線"]),
    ("東京メトロ", "丸ノ内線", ["丸ノ内"]),
    ("東京メトロ", "日比谷線", ["日比谷"]),
    ("東京メトロ", "東西線", ["東西線"]),
    ("東京メトロ", "千代田線", ["千代田"]),
    ("東京メトロ", "有楽町線", ["有楽町線"]),
    ("東京メトロ", "半蔵門線", ["半蔵門"]),
    ("東京メトロ", "南北線", ["南北線"]),
    ("東京メトロ", "副都心線", ["副都心"]),
    ("都営地下鉄", "都営浅草線", ["浅草線"]),
    ("都営地下鉄", "都営三田線", ["三田線"]),
    ("都営地下鉄", "都営新宿線", ["都営新宿"]),
    ("都営地下鉄", "都営大江戸線", ["大江戸"]),
    ("東急", "東急東横線", ["東横"]),
    ("東急", "東急目黒線", ["目黒線"]),
    ("東急", "東急田園都市線", ["田園都市"]),
    ("東急", "東急大井町線", ["大井町"]),
    ("東急", "東急池上線", ["池上"]),
    ("東急", "東急多摩川線", ["東急多摩川"]),
    ("東急", "東急世田谷線", ["世田谷線"]),
    ("東急", "東急こどもの国線", ["こどもの国"]),
    ("京王", "京王線", ["京王線"]),
    ("京王", "京王新線", ["京王新線"]),
    ("京王", "京王井の頭線", ["井の頭"]),
    ("京王", "京王相模原線", ["相模原線"]),
    ("京王", "京王高尾線", ["高尾線"]),
    ("小田急", "小田急小田原線", ["小田原線", "小田急小田原"]),
    ("小田急", "小田急江ノ島線", ["江ノ島線", "江の島線"]),
    ("小田急", "小田急多摩線", ["小田急多摩"]),
    ("京急", "京急本線", ["京急本線"]),
    ("京急", "京急空港線", ["京急空港", "空港線"]),
    ("京急", "京急逗子線", ["逗子線"]),
    ("京急", "京急久里浜線", ["久里浜"]),
    ("京急", "京急大師線", ["京急大師"]),
    ("京成", "京成本線", ["京成本線"]),
    ("京成", "京成押上線", ["押上"]),
    ("京成", "京成千葉線", ["京成千葉", "千葉線"]),
    ("京成", "京成金町線", ["金町"]),
    ("京成", "京成千原線", ["千原"]),
    ("京成", "成田スカイアクセス線", ["スカイアクセス", "成田空港線"]),
    ("東武", "東武スカイツリーライン(伊勢崎線)", ["スカイツリー", "伊勢崎線"]),
    ("東武", "東武東上線", ["東上"]),
    ("東武", "東武アーバンパークライン(野田線)", ["アーバンパーク", "野田線"]),
    ("東武", "東武亀戸線", ["亀戸線"]),
    ("東武", "東武大師線", ["東武大師"]),
    ("西武", "西武池袋線", ["西武池袋", "池袋線"]),
    ("西武", "西武新宿線", ["西武新宿"]),
    ("西武", "西武拝島線", ["拝島"]),
    ("西武", "西武多摩湖線", ["多摩湖"]),
    ("西武", "西武国分寺線", ["国分寺線"]),
    ("西武", "西武園線", ["西武園"]),
    ("西武", "西武豊島線", ["豊島線"]),
    ("西武", "西武有楽町線", ["西武有楽町"]),
    ("西武", "西武多摩川線", ["西武多摩川", "是政"]),
    ("相鉄", "相鉄本線", ["相鉄本線"]),
    ("相鉄", "相鉄いずみ野線", ["いずみ野"]),
    ("相鉄", "相鉄新横浜線", ["相鉄新横浜"]),
    ("横浜市交・MM", "横浜市営ブルーライン", ["ブルーライン"]),
    ("横浜市交・MM", "横浜市営グリーンライン", ["グリーンライン"]),
    ("横浜市交・MM", "みなとみらい線", ["みなとみらい"]),
    ("モノレール・新交通", "多摩都市モノレール", ["多摩都市モノレール", "多摩モノレール"]),
    ("モノレール・新交通", "千葉都市モノレール", ["千葉都市モノレール", "千葉モノレール"]),
    ("モノレール・新交通", "湘南モノレール", ["湘南モノレール"]),
    ("モノレール・新交通", "日暮里・舎人ライナー", ["舎人"]),
    ("モノレール・新交通", "ゆりかもめ", ["ゆりかもめ"]),
    ("モノレール・新交通", "ニューシャトル", ["ニューシャトル", "埼玉新都市"]),
    ("その他私鉄", "つくばエクスプレス", ["つくば", "ＴＸ", "TX"]),
    ("その他私鉄", "りんかい線", ["りんかい"]),
    ("その他私鉄", "新京成線", ["新京成"]),
    ("その他私鉄", "北総線", ["北総"]),
    ("その他私鉄", "東葉高速線", ["東葉"]),
    ("その他私鉄", "埼玉高速鉄道", ["埼玉高速", "埼玉スタジアム"]),
    ("その他私鉄", "流鉄流山線", ["流鉄", "流山線"]),
    ("その他私鉄", "山万ユーカリが丘線", ["山万", "ユーカリが丘線"]),
    ("その他私鉄", "伊豆箱根鉄道大雄山線", ["大雄山", "伊豆箱根"]),
    ("その他私鉄", "秩父鉄道", ["秩父鉄道", "秩父線"]),
    ("その他私鉄", "江ノ電", ["江ノ電", "江ノ島電鉄"]),
    ("都電", "都電荒川線(さくらトラム)", ["荒川線", "さくらトラム", "都電"]),
]
LABEL_ORDER = [label for _, label, _ in TAXONOMY]
LABEL_RANK = {label: i for i, label in enumerate(LABEL_ORDER)}
LINE_SUFFIXES = ("エクスプレス", "モノレール", "ライナー", "トラム", "ライン", "線")


def expand_lines_text(paren: str) -> str:
    """圧縮された路線表記を各路線名へ展開する。
    例「JR中央・横浜・八高線」→「JR中央線・横浜線・八高線」
       「有楽町・副都心線」→「有楽町線・副都心線」
    末尾トークンが持つ接尾辞(線/ライン等)を、接尾辞のない先行トークンに補う。
    """
    out = []
    for chunk in re.split(r"[/／]", paren):
        toks = chunk.split("・")
        suf = ""
        for t in reversed(toks):
            for s in LINE_SUFFIXES:
                if t.endswith(s):
                    suf = s
                    break
            if suf:
                break
        rebuilt = []
        for t in toks:
            t = t.strip()
            if not t:
                continue
            if any(t.endswith(s) for s in LINE_SUFFIXES) or not suf:
                rebuilt.append(t)
            else:
                rebuilt.append(t + suf)
        out.append("・".join(rebuilt))
    return "／".join(out)


def extract_lines(heading: str) -> list[str]:
    """駅見出しの括弧内から正準路線ラベルのリストを返す（タクソノミ順）。"""
    parens = re.findall(r"[（(]([^)）\n]+)[）)]", heading)
    if not parens:
        return []
    raw = "／".join(parens)
    expanded = expand_lines_text(raw)
    found = set()
    for _, label, kws in TAXONOMY:
        if any(k in expanded for k in kws):
            found.add(label)

    def has(*xs):
        return any(x in expanded for x in xs)

    def has_company(prefix):
        return any(l.startswith(prefix) for l in found)

    # 会社名のみの表記（例「（小田急）」「（京急）」「（東武）」）は各社の本線/主要線へ寄せる
    if "小田急" in expanded and not has("江ノ島", "小田急多摩"):
        found.add("小田急小田原線")
    if "京急" in expanded and not has("空港", "逗子", "久里浜", "大師"):
        found.add("京急本線")
    if "京成" in expanded and not has("押上", "千葉線", "京成千葉", "金町", "スカイアクセス", "千原"):
        found.add("京成本線")
    if "相鉄" in expanded and not has_company("相鉄"):
        found.add("相鉄本線")
    if "東急" in expanded and not has_company("東急"):
        found.add("東急東横線")
    if "東武" in expanded and not has_company("東武"):
        found.add("東武スカイツリーライン(伊勢崎線)")
    # 横浜市営地下鉄: 線名なしの「市営地下鉄」は中心部＝ブルーライン
    if "市営地下鉄" in expanded and "グリーンライン" not in expanded:
        found.add("横浜市営ブルーライン")
    # 「JR各線」やバールの「JR」のみ（大ターミナル）
    tokens = re.split(r"[／/・,、\s]+", raw)
    if "JR各線" in raw or any(t in ("JR", "ＪＲ", "JR線", "JR各線") for t in tokens):
        found.add("JR各線（大ターミナル）")

    return sorted(found, key=lambda l: LABEL_RANK.get(l, 999))


# ---- 新店（2026年オープン）判定 ----
_OPEN_KW = ("開店", "開業", "オープン", "新規", "新店", "進出")
_REOPEN_KW = ("再開", "リニューアル", "移転", "復活")
_AWARD_KW = ("百名店", "百", "TRY", "EAST", "WEST", "大賞", "グランプリ", "オブ", "受賞", "ミシュラン", "ビブ")


# ---- 深夜営業（夜遅くまで）判定 ----
_LATE_KW = ("深夜", "翌1", "翌2", "翌3", "翌4", "24時間", "〜24", "1時まで", "2時まで",
            "朝まで", "23時", "〜23")


def is_late_night(feat: str) -> bool:
    """夜遅く（深夜帯）まで営業している手がかりが特徴テキストにあるか。"""
    return any(k in feat for k in _LATE_KW)


# ---- 夜営業（18〜21時台に営業）判定 ----
# DBは営業時間の構造化データを持たないため、「昼のみ・早仕舞い」が明記された店を
# 除外し、残りを“夜も営業している可能性が高い”店として扱う実用フィルタ。
# （深夜営業店は当然 is_lunch_only に該当せず夜営業に含まれる。個別の営業時間は未検証。）
_LUNCH_ONLY_KW = ("昼のみ", "昼営業のみ", "昼の部のみ", "昼限定", "昼だけ", "日中のみ",
                  "朝のみ", "朝ラーのみ", "朝専門",
                  "〜14時", "〜15時", "〜16時", "14時まで", "15時まで", "16時まで")


def is_lunch_only(feat: str) -> bool:
    """昼のみ・早仕舞い（夜は営業しない）と明記されているか。"""
    return any(k in feat for k in _LUNCH_ONLY_KW)


def is_new_2026(feat: str) -> bool:
    """特徴テキストから「2026年オープンの新店」を判定する。
    受賞年（例「EAST百名店2026」）や再開・移転・リニューアルは除外する。
    """
    for m in re.finditer(r"2026", feat):
        s, e = m.start(), m.end()
        before = feat[max(0, s - 6):s]
        if any(a in before for a in _AWARD_KW):
            continue  # 「百名店2026」等の受賞年
        window = feat[max(0, s - 8):e + 12]
        if not any(k in window for k in _OPEN_KW):
            continue  # 開店系の語が近くにない
        if any(k in window for k in _REOPEN_KW):
            continue  # 再開・移転・リニューアルは新店扱いしない
        return True
    return False


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


# ---- 西新宿からの所要時間（目安）----
# ユーザーの最寄り＝西新宿（丸ノ内線・新宿の1駅隣）を起点に、各店の最寄駅までの
# おおよその所要時間（分）を、区/市の代表値＋主要駅の個別補正で推定する。
# 実経路APIではなく路線・距離からの“目安”。表示は時間帯バンド（4段階）。
WARD_MIN = {
    # 東京23区
    "新宿区": 8, "渋谷区": 12, "中野区": 12, "杉並区": 16, "豊島区": 13,
    "千代田区": 20, "中央区": 24, "港区": 20, "文京区": 18, "品川区": 20,
    "目黒区": 18, "世田谷区": 22, "台東区": 30, "墨田区": 30, "江東区": 33,
    "荒川区": 28, "足立区": 35, "葛飾区": 42, "江戸川区": 40, "北区": 22,
    "板橋区": 24, "練馬区": 22,
    # 多摩
    "吉祥寺・三鷹・小金井": 22, "立川・国立・国分寺・昭島": 30,
    "八王子・日野・多摩": 45, "西東京・小平・東久留米・東村山・清瀬": 32,
    "調布・府中・狛江": 26, "町田": 33,
    # 神奈川
    "横浜中心部": 36, "横浜北部": 35, "横浜南西部": 48,
    "川崎市南部": 28, "川崎市北部": 32, "県央・相模原": 48, "湘南・県西": 65,
    # 埼玉
    "さいたま市": 32, "さいたま市北部": 33, "埼玉": 58,
    "川口・蕨・戸田": 28, "越谷・草加・春日部": 45, "西武沿線エリア": 38,
    "川越・東武東上線": 52,
    # 千葉
    "千葉市": 50, "千葉郊外": 52, "市川・浦安": 35, "松戸・柏": 42,
    "船橋・習志野": 44, "流山・我孫子・野田・鎌ヶ谷": 52,
}
# 区/市の代表値と異なる主要駅の個別補正（駅名は「駅」「停留場」を除いた正規形）
STATION_MIN = {
    "西新宿": 2, "新宿": 4, "西新宿五丁目": 5, "新宿三丁目": 5, "都庁前": 6,
    "渋谷": 6, "代々木": 6, "中野": 6, "東中野": 5, "中野坂上": 4,
    "高田馬場": 8, "池袋": 8, "代々木上原": 9, "下北沢": 9, "中目黒": 13,
    "恵比寿": 13, "大崎": 13, "五反田": 16, "目黒": 14, "池尻大橋": 14,
    "三軒茶屋": 17, "飯田橋": 12, "市ヶ谷": 13, "市ケ谷": 13, "九段下": 15,
    "後楽園": 12, "春日": 12, "江戸川橋": 13, "茗荷谷": 14,
    "表参道": 12, "外苑前": 13, "青山一丁目": 13, "六本木": 14, "六本木一丁目": 15,
    "麻布十番": 17, "吉祥寺": 16, "国分寺": 26, "国立": 30, "立川": 30,
    "昭島": 40, "拝島": 45, "八王子": 45, "高尾": 52, "町田": 32,
    "大宮": 30, "浦和": 28, "北浦和": 30, "上尾": 42, "桶川": 46, "鴻巣": 46,
    "熊谷": 58, "本庄": 70, "深谷": 66, "川越": 52, "本川越": 55,
    "横浜": 32, "関内": 42, "桜木町": 40, "川崎": 30, "武蔵小杉": 22,
    "新横浜": 30, "藤沢": 52, "茅ケ崎": 58, "平塚": 62, "小田原": 80,
    "鎌倉": 58, "大船": 48, "西船橋": 35, "船橋": 40, "津田沼": 44,
    "千葉": 48, "柏": 46, "松戸": 36, "浦安": 32,
}
BAND_LABEL = {1: "〜20分", 2: "20〜40分", 3: "40〜60分", 4: "60分〜"}


def _norm_station(name: str) -> str:
    name = re.sub(r"[（(].*?[）)]", "", name)
    for suf in ("停留場", "駅前", "駅"):
        if name.endswith(suf):
            return name[: -len(suf)].strip()
    return name.strip()


def _stations_from_locs(ward: str, locs: list[str]) -> list[str]:
    """locs(['区・駅名', ...])から駅名トークンを取り出す。複数駅併記も分割。"""
    out = []
    for loc in locs:
        if loc.startswith(ward + "・"):
            sp = loc[len(ward) + 1:]
        elif loc == ward:
            continue
        else:
            sp = loc
        for part in re.split(r"\s*/\s*|・", sp):
            part = part.strip()
            if part:
                out.append(part)
    return out


def travel_minutes(ward: str, locs: list[str]) -> int:
    """西新宿からの目安所要時間（分）。複数駅に該当する店は最短を採用。"""
    base = WARD_MIN.get(ward, 40)
    best = base
    found = False
    for st in _stations_from_locs(ward, locs):
        v = STATION_MIN.get(_norm_station(st), base)
        if not found or v < best:
            best, found = v, True
    return best


def travel_band(minutes: int) -> int:
    if minutes <= 20:
        return 1
    if minutes <= 40:
        return 2
    if minutes <= 60:
        return 3
    return 4


def annotate(records: list[dict]) -> None:
    """夜営業フラグと西新宿からの所要時間バンドを各レコードに付与する。"""
    for r in records:
        r["lunch_only"] = bool(r.get("lunch_only"))
        r["evening"] = not r["lunch_only"]
        m = travel_minutes(r["ward"], r["locs"])
        r["travel_min"] = m
        r["travel_band"] = travel_band(m)


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
                    rec["lines"].sort(key=lambda l: LABEL_RANK.get(l, 999))
                    rec["new_shop"] = rec["new_shop"] or is_new_2026(feat)
                    rec["late_night"] = rec["late_night"] or is_late_night(feat)
                    rec["lunch_only"] = rec["lunch_only"] or is_lunch_only(feat)
                    continue
                bykey[key] = dict(pref=pref, ward=ward, station=station, shop=shop,
                                  genre=genre, feat=feat, ev=ev, src=src, url=url, locs=[loc],
                                  lines=list(current_lines),
                                  closed_days=parse_closed_days(feat),
                                  new_shop=is_new_2026(feat),
                                  late_night=is_late_night(feat),
                                  lunch_only=is_lunch_only(feat))
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
    late = [r for r in records if r.get("late_night")]
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
            "awards", "feature", "source_url", "closed_days", "lines", "new_2026",
            "late_night", "evening", "lunch_only", "travel_min", "travel_band"]
    with open(os.path.join(DATA, "ramen.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r["shop"], r["pref"], r["ward"], " / ".join(r["locs"]), r["genre"],
                        "/".join(classify(r["genre"])), score(r["ev"]) or "",
                        ";".join(awards_of(r)), r["feat"], r["url"],
                        ";".join(r.get("closed_days", [])),
                        " / ".join(r.get("lines", [])),
                        "1" if r.get("new_shop") else "",
                        "1" if r.get("late_night") else "",
                        "1" if r.get("evening") else "",
                        "1" if r.get("lunch_only") else "",
                        r.get("travel_min", ""),
                        r.get("travel_band", "")])
    arr = [dict(shop=r["shop"], pref=r["pref"], ward=r["ward"], stations=r["locs"], genre=r["genre"],
               genres=classify(r["genre"]), tabelog_score=(score(r["ev"]) or None),
               awards=awards_of(r), feature=r["feat"], source_url=r["url"],
               closed_days=r.get("closed_days", []),
               lines=r.get("lines", []),
               new_shop=bool(r.get("new_shop")),
               late_night=bool(r.get("late_night")),
               evening=bool(r.get("evening")),
               lunch_only=bool(r.get("lunch_only")),
               travel_min=r.get("travel_min"),
               travel_band=r.get("travel_band")) for r in rows]
    payload = json.dumps(arr, ensure_ascii=False, indent=2)
    with open(os.path.join(DATA, "ramen.json"), "w", encoding="utf-8") as f:
        f.write(payload)
    # GitHub Pages のビューア(docs/index.html)から相対参照するため docs/data にも複製
    with open(os.path.join(DOCS, "data", "ramen.json"), "w", encoding="utf-8") as f:
        f.write(payload)
    return len(rows)


def write_lines(records):
    """ビューアの路線プルダウン用に、データ中に実在する路線を
    鉄道会社ごと(タクソノミ順)にグループ化して lines.json に出力する。"""
    counts = defaultdict(int)
    for r in records:
        for l in r.get("lines", []):
            counts[l] += 1
    groups = []
    for company, label, _ in TAXONOMY:
        if not counts.get(label):
            continue
        if not groups or groups[-1]["company"] != company:
            groups.append(dict(company=company, lines=[]))
        groups[-1]["lines"].append(dict(label=label, count=counts[label]))
    payload = json.dumps(groups, ensure_ascii=False, indent=2)
    for d in (DATA, os.path.join(DOCS, "data")):
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "lines.json"), "w", encoding="utf-8") as f:
            f.write(payload)
    return sum(len(g["lines"]) for g in groups)


def main() -> None:
    records = parse_records()
    annotate(records)
    os.makedirs(OUT, exist_ok=True)
    by_genre = write_genre(records)
    star, bib, hyaku = write_awards(records)
    late, morning, reserve, queue, hall = write_practical(records)
    fams = write_lineage(records)
    n = write_data(records)
    nlines = write_lines(records)
    n_new = sum(1 for r in records if r.get("new_shop"))
    n_sun = sum(1 for r in records if "Sun" not in r.get("closed_days", []))
    n_night = sum(1 for r in records if r.get("late_night"))
    n_evening = sum(1 for r in records if r.get("evening"))
    n_lunch = sum(1 for r in records if r.get("lunch_only"))
    bands = defaultdict(int)
    for r in records:
        bands[r.get("travel_band")] += 1
    print(f"records={len(records)} csv/json={n}")
    print(f"awards: star={len(star)} bib={len(bib)} hyaku={len(hyaku)}")
    print(f"practical: late={len(late)} morning={len(morning)} reserve={len(reserve)} queue={len(queue)} hall={len(hall)}")
    print(f"lines in dropdown={nlines}  new_2026={n_new}  open_sunday={n_sun}  late_night(深夜)={n_night}")
    print(f"evening(夜営業)={n_evening}  lunch_only(昼のみ)={n_lunch}")
    print(f"travel bands from 西新宿 (1:〜20/2:〜40/3:〜60/4:60+): "
          + "  ".join(f"{b}={bands[b]}" for b in (1, 2, 3, 4)))
    print("new_2026 shops:", [r["shop"] for r in records if r.get("new_shop")])
    print("lineage families:")
    for name, uniq in fams:
        print(f"  {name}: {len(uniq)}")


if __name__ == "__main__":
    main()
