#!/usr/bin/env python3
"""Add verified 2026 new shops to the ramen DB markdown files."""
import sys

BASE = "/home/user/RamenResearch"

def add_rows(file_path, heading_substr, new_rows):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    heading_idx = None
    for i, line in enumerate(lines):
        if heading_substr in line and (line.startswith('## ') or line.startswith('### ')):
            heading_idx = i
            break
    if heading_idx is None:
        print(f"  WARN: heading not found: {heading_substr!r}", file=sys.stderr)
        return False
    last_table_idx = None
    for i in range(heading_idx + 1, len(lines)):
        line = lines[i].rstrip('\n')
        if line.startswith('## ') or line.startswith('### ') or line == '---':
            break
        if line.startswith('|') and not line.startswith('|---'):
            last_table_idx = i
    if last_table_idx is None:
        print(f"  WARN: no table rows after: {heading_substr!r}", file=sys.stderr)
        return False
    insert = [row + '\n' for row in new_rows]
    lines = lines[:last_table_idx + 1] + insert + lines[last_table_idx + 1:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"  + {len(new_rows)} rows → '{heading_substr}' in {file_path.split('/')[-1]}")
    return True

def add_section_before(file_path, before_substr, section_lines):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    idx = None
    for i, line in enumerate(lines):
        if before_substr in line and (line.startswith('### ') or line.startswith('## ')):
            idx = i
            break
    if idx is None:
        idx = len(lines)
    insert = [l + '\n' for l in section_lines]
    lines = lines[:idx] + insert + lines[idx:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"  + new section before '{before_substr}' in {file_path.split('/')[-1]}")

INSERTIONS = [
    # 千代田区
    (f"{BASE}/regions/tokyo/01_chiyoda.md", "神田駅（JR山手", [
        "| 神田煮干中華蕎麦 まいまい | 煮干し中華そば | 亀戸「つきひ」系列3号店、煮干主役の清湯・濃厚2種、2026年4月開店 | 食べログ3.16 | [食べログ](https://tabelog.com/tokyo/A1310/A131002/13319835/) |",
        "| 一天門 神田店 | 和風豚骨（博多系） | 博多中洲川端の行列店東京初進出、青唐辛子「青ダレ」入り、2026年5月開店 | 点数未確定（新店） | [食べログ](https://tabelog.com/tokyo/A1310/A131002/13322359/) |",
    ]),
    (f"{BASE}/regions/tokyo/01_chiyoda.md", "淡路町駅（丸ノ内線）", [
        "| 伊達商店 淡路町店 | 発酵調味料・味噌/醤油中華そば | 鹿児島創業200年「伊達醸造」東京初の路面常設店、麦味噌「核威味噌」など、2026年5月開店 | 点数未確定（新店） | [食べログ](https://tabelog.com/tokyo/A1310/A131002/13322616/) |",
    ]),
    # 港区
    (f"{BASE}/regions/tokyo/03_minato.md", "新橋駅（JR各線", [
        "| 中華そば 喜長 | つけ麺・中華そば（丸長系） | 神田「ラーメンわいず」系列、荻窪丸長インスパイア・黒甘辛酸つけ汁、深夜行列、2026年3月開店 | 食べログ3.42 | [食べログ](https://tabelog.com/tokyo/A1301/A130103/13320108/) |",
    ]),
    (f"{BASE}/regions/tokyo/03_minato.md", "広尾駅（日比谷線）", [
        "| CRAFT NOODLES はしづめ | 創作麺（選べる麺×和食材出汁） | ミシュラン一つ星シェフ監修、8種の麺×8種メニュー、日曜定休、2026年4月開店 | 食べログ3.08 | [PR Times](https://prtimes.jp/main/html/rd/p/000000004.000101505.html) |",
    ]),
    # 新宿区
    (f"{BASE}/regions/tokyo/04_shinjuku.md", "高田馬場駅（JR山手線", [
        "| RAMEN 紫苑 | 塩ラーメン（無化調・地鶏コンソメ） | 長州黒かしわ等地鶏使用、L字8席QR注文、昼のみ行列、2026年3月開店 | 食べログ3.61 | [食べログ](https://tabelog.com/tokyo/A1305/A130503/13319655/) |",
    ]),
    (f"{BASE}/regions/tokyo/04_shinjuku.md", "新大久保駅（JR山手線）", [
        "| 一匠 | 豚骨ラーメン（ワンタン） | 野中家プロデュース、深夜3時まで、ライス食べ放題、2026年3月開店 | 食べログ3.09 | [食べログ](https://tabelog.com/tokyo/A1304/A130404/13319796/) |",
    ]),
    (f"{BASE}/regions/tokyo/04_shinjuku.md", "新宿駅（JR各線", [
        "| 萬馬軒 新宿西口本店 | 濃厚味噌ラーメン | 「萬馬軒」旗艦店・西口徒歩5分、開店日は味噌600円、11〜23時、2026年2月開店 | 点数未確定（新店） | [PR Times](https://prtimes.jp/main/html/rd/p/000000234.000027681.html) |",
    ]),
    (f"{BASE}/regions/tokyo/04_shinjuku.md", "都庁前駅（都営大江戸線）", [
        "| らーめん 鴨to葱 新宿西口店 | 鴨ラーメン | 上野「鴨to葱」系列、合鴨と葱・水のみで炊いた澄んだ鴨だし、2026年4月開店 | 食べログ3.08 | [食べログ](https://tabelog.com/tokyo/A1304/A130401/13321726/) |",
    ]),
    # 文京区
    (f"{BASE}/regions/tokyo/05_bunkyo.md", "江戸川橋駅（有楽町線）", [
        "| 中華そば くおん | 煮干し中華そば | 飯能「flour works」公認、煮干100%「香澄」と動物系「TOKYO CLASSIC」2種、水曜定休、2026年2月開店 | 食べログ3.51 | [食べログ](https://tabelog.com/tokyo/A1309/A130905/13319106/) |",
        "| 大関家 | 家系 | 大輝家グループの新店、元・春樹跡地、2026年5月開店 | 点数未確定（新店） | [食べログ](https://tabelog.com/tokyo/A1309/A130905/13322667/) |",
    ]),
    # 台東区
    (f"{BASE}/regions/tokyo/06_taito.md", "浅草駅（銀座線", [
        "| ラーメン ニクノイロ | 肉系ラーメン（醤油・塩） | 浅草地下街の肉特化新店、チャーシュー大盛り、2026年5月開店 | 点数未確定（新店） | [号外NET](https://taito.goguynet.jp/2026/05/14/nikunoiro/) |",
        "| Gion Duck Noodles Asakusa | 鴨出汁ラーメン（清湯/白湯） | 京都祇園の人気鴨そば店東京初進出、ドイツ産ライ麦麺、2026年4月開店 | 食べログ3.07 | [食べログ](https://tabelog.com/en/tokyo/A1311/A131102/13321294/) |",
    ]),
    (f"{BASE}/regions/tokyo/06_taito.md", "浅草橋駅（JR総武線", [
        "| 麺家 笑の道 | 横浜家系（鶏×醤油） | 「麺家たいせい」系列3号店、初日419人の大行列、2026年5月開店 | 点数未確定（新店） | [食べログ](https://tabelog.com/tokyo/A1311/A131103/13321733/) |",
    ]),
    (f"{BASE}/regions/tokyo/06_taito.md", "上野広小路駅（銀座線）", [
        "| 拘り麺屋 へご | 鶏淡麗醤油ラーメン | 愛媛・四国中央市「みしまや」東京初進出、土日祝定休、仲御徒町至近、2026年4月開店 | 食べログ3.05 | [区民ニュース](https://kumin.news/taito/articles/1266847) |",
    ]),
    (f"{BASE}/regions/tokyo/06_taito.md", "三ノ輪駅（東京メトロ日比谷線）", [
        "| 博多らーめん 一心堂 三ノ輪店 | 博多豚骨（黒・白・赤） | 十条の創業13年店の2号店、つけ麺・担々麺・油そばも、2026年1月開店 | 食べログ3.06 | [号外NET](https://taito.goguynet.jp/2026/02/09/hakata/) |",
    ]),
    (f"{BASE}/regions/tokyo/06_taito.md", "浅草駅（つくばエクスプレス）", [
        "| 中華そば 五郎 浅草店 | 中華そば（動物系あっさり） | 共立メンテナンス運営、塩・味噌・あさり等多種、年中無休11〜21時、2026年2月開店 | 食べログ3.06 | [PR Times](https://prtimes.jp/main/html/rd/p/000000442.000030012.html) |",
    ]),
    # 墨田区
    (f"{BASE}/regions/tokyo/07_sumida.md", "錦糸町駅（JR総武線", [
        "| なぎちゃんラーメン 錦糸町店 | ちゃん系ラーメン（煮干し） | 「凪」グループのちゃん系ブランド、赤看板に白抜き文字、2026年1月開店 | 食べログ3.42 | [号外NET](https://sumida.goguynet.jp/2025/12/14/nagichan-open/) |",
        "| 麺屋 旭 錦糸町店 | 横浜家系 | 大輝家直系の2号店、開店記念で味玉食べ放題、2026年3月開店 | 食べログ3.30 | [号外NET](https://sumida.goguynet.jp/2026/03/21/menyaasahi-open/) |",
    ]),
    # 江東区
    (f"{BASE}/regions/tokyo/08_koto.md", "南砂町駅（東西線）", [
        "| RAMEN MUROHOUSE | こく醤油ラーメン | 八王子百名店「鴨福」出身、初日大行列カウンター6席、月・金定休、2026年4月開店 | 食べログ3.07 | [俺ラーメン](https://ore-ramen.com/murohouse) |",
    ]),
    (f"{BASE}/regions/tokyo/08_koto.md", "住吉駅（半蔵門線", [
        "| タンメン トナリ 住吉店 | タンメン専門 | 「トナリ」が創業の地・江東区に出した新店、10:30〜22:00、2026年4月開店 | 食べログ3.10 | [PR Times](https://prtimes.jp/main/html/rd/p/000000074.000087198.html) |",
    ]),
    (f"{BASE}/regions/tokyo/08_koto.md", "大島駅・西大島駅", [
        "| ジョニーヌードル 大島店 | 中華そば・担々麺 | 麹町・半蔵門「ジョニーヌードル」系列、「純手打ち麺きらく」跡地、2026年5月開店 | 食べログ3.04 | [号外NET](https://koto.goguynet.jp/2026/04/11/johnny_noodle_ojima/) |",
    ]),
    (f"{BASE}/regions/tokyo/08_koto.md", "亀戸駅（JR総武線）", [
        "| 十六代目 野中家 亀戸店 | 横浜家系 | 野中家グループの新店、開店2日間初日500円、2026年5月開店 | 点数未確定（新店） | [公式X](https://x.com/Nonakaya_G/status/2045892286253535541) |",
    ]),
    # 品川区
    (f"{BASE}/regions/tokyo/09_shinagawa.md", "五反田駅（JR山手", [
        "| 焼きあご塩らー麺たかはし 五反田店 | 焼きあご塩ラーメン | トビウオ出汁の中濃塩スープ、深夜28時まで、都内7店目、2026年3月開店 | 食べログ3.18 | [品川経済新聞](https://shinagawa.keizai.biz/headline/4987/) |",
    ]),
    (f"{BASE}/regions/tokyo/09_shinagawa.md", "大井町駅（JR京浜東北", [
        "| 玉（GYOKU） 大井町トラックス店 | 濃厚魚介つけ麺・ラーメン | 新商業施設「OIMACHI TRACKS」3F、2026年3月開店 | 食べログ3.13 | [公式](https://www.gyoku.co.jp/contents/category/oimachi-tracks) |",
        "| どうとんぼり神座 OIMACHI TRACKS店 | ラーメン（おいしいラーメン） | 「OIMACHI TRACKS」2F、2026年3月開店 | 食べログ3.03 | [公式](https://kamukura.co.jp/shop/10553/) |",
    ]),
    (f"{BASE}/regions/tokyo/09_shinagawa.md", "武蔵小山駅（東急目黒線）", [
        "| なぎちゃんラーメン 武蔵小山店 | ちゃん系（煮干し）ラーメン | 「凪」グループのちゃん系ブランド、パルム商店街「パンの田島」跡地、2026年2月開店 | 食べログ3.37 | [号外NET](https://shinagawa.goguynet.jp/2026/02/20/nagichannra-mennmusashikoyamatenn-2/) |",
    ]),
    (f"{BASE}/regions/tokyo/09_shinagawa.md", "青物横丁駅（京急本線）", [
        "| なぎちゃんラーメン 青物横丁店 | ちゃん系（煮干し）ラーメン | 「凪」グループのちゃん系ブランド、駅至近、2026年1月開店 | 食べログ3.41 | [食べログ](https://tabelog.com/tokyo/A1315/A131501/13317715/) |",
    ]),
    # 目黒区
    (f"{BASE}/regions/tokyo/10_meguro.md", "中目黒駅（日比谷線", [
        "| 中華たかまる | 町中華系ラーメン | 西葛西「ラーメンの王様」出身、スタミナ系の看板メニュー、2026年2月開店 | 食べログ3.08 | [食べログ](https://tabelog.com/tokyo/A1317/A131701/13318562/) |",
    ]),
    (f"{BASE}/regions/tokyo/10_meguro.md", "自由が丘駅（東急東横線", [
        "| 鶏のとりこ 自由が丘店 | 濃厚魚介鶏白湯 | 新橋「麺屋 周郷」直伝、「塩そば 一榮」からの業態変更リニューアル、2026年4月開店 | 食べログ3.06 | [号外NET](https://meguro.goguynet.jp/2026/04/30/torinotoriko_jiyugaoka/) |",
    ]),
    # 大田区
    (f"{BASE}/regions/tokyo/11_ota.md", "蒲田駅（JR京浜東北", [
        "| ラーメンステーション蒲田 | 鶏塩/海老塩ラーメン（豚肉不使用） | 大阪「らーめん香澄」監修、ハラール対応・定休日なし、2026年4月開店 | 食べログ3.12 | [PR Times](https://prtimes.jp/main/html/rd/p/000000062.000073406.html) |",
    ]),
    (f"{BASE}/regions/tokyo/11_ota.md", "大森駅（JR京浜東北）", [
        "| 三代目 らーめん谷瀬家 | 家系ラーメン | 新橋本店・神田に次ぐ3号店、日曜定休、2026年4月開店 | 食べログ3.08 | [食べログ](https://tabelog.com/tokyo/A1315/A131502/13319602/) |",
    ]),
    (f"{BASE}/regions/tokyo/11_ota.md", "梅屋敷駅・大森町駅（京急本線）", [
        "| 麺屋FLOW | 醤油・塩ラーメン（黒トリュフ系） | 黒トリュフ薫醤油・柚子薫塩、1日100食限定スープ切れ終了、2026年4月開店 | 食べログ3.08 | [食べログ](https://tabelog.com/tokyo/A1315/A131503/13320166/) |",
    ]),
    # 世田谷区
    (f"{BASE}/regions/tokyo/12_setagaya.md", "下北沢駅（小田急", [
        "| あはれ | まぜそば・仙台辛味噌まぜそば | 仙台ラーメンWalkerグランプリ金賞の凱旋店、仙台辛味噌まぜそばが看板、2026年5月開店 | 食べログ3.03 | [PR Times](https://prtimes.jp/main/html/rd/p/000000028.000045707.html) |",
        "| 背脂ラーメンチャッチャ亭 下北沢店 | 背脂ラーメン | 下北沢駅至近の背脂系新店舗、2026年5月開店 | 食べログ3.01 | [食べログ](https://tabelog.com/tokyo/A1318/A131802/13322...) |",
    ]),
    (f"{BASE}/regions/tokyo/12_setagaya.md", "三軒茶屋駅（東急田園都市線", [
        "| 中華そば つぼ | 背脂煮干し中華そば | 茶沢通り沿い、木曜定休・昼営業中心、2026年4月開店 | 食べログ3.05 | [食べログ](https://tabelog.com/tokyo/A1317/A131706/13321151/) |",
    ]),
    # 渋谷区
    (f"{BASE}/regions/tokyo/13_shibuya.md", "笹塚駅（京王線", [
        "| 横浜家系ラーメン みどり 笹塚店 | 家系 | らぁ麺はやし田グループ㈱INGSの2号店、開店2日間500円、11〜23時、2026年3月開店 | 食べログ3.13 | [食べログ](https://tabelog.com/tokyo/A1318/A131808/13319786/) |",
        "| 白鶏舎 笹塚店 | 鶏白湯 | 札幌㈱イーストンの東京初進出、昼は白鶏舎・夜は焼手羽「トリノイロ」の二毛作、2026年4月開店 | 食べログ3.05 | [PR Times](https://prtimes.jp/main/html/rd/p/000000194.000078678.html) |",
    ]),
    (f"{BASE}/regions/tokyo/13_shibuya.md", "渋谷駅（JR山手", [
        "| SHOJIN RAMEN 菜（さい） | ヴィーガンラーメン | 女性店主の完全植物性専門店、柚子塩・豚骨風ヴィーガン等、深夜3時まで、2026年4月開店 | 食べログ3.05 | [食べログ](https://tabelog.com/tokyo/A1303/A130301/13321462/) |",
        "| ご縁 | 油そば（松阪豚×ブランド卵） | 会員制高級寿司「鮨逅」姉妹店、「油そば 結」980円・朝10時開店、2026年4月開店 | 食べログ3.09 | [食べログ](https://tabelog.com/tokyo/A1303/A130301/13321380/) |",
        "| 麺屋 さか元 | まぜそば（ホルモン台湾まぜそば） | 焼肉「元家別邸」の平日昼限定ブランド、土日祝休、2026年4月開店 | 食べログ3.08 | [食べログ](https://tabelog.com/tokyo/A1303/A130301/13320736/) |",
    ]),
    # 中野区
    (f"{BASE}/regions/tokyo/14_nakano.md", "東中野駅（JR中央・総武緩行", [
        "| 山喜多製麺所 | 味噌ラーメン（鉄鍋焼みそ） | 居酒屋「日本橋やまきた」系の初ラーメン業態、蔵元伝承みそ「鉄鍋焼みそ」が看板、2026年1月開店 | 食べログ3.24 | [食べログ](https://tabelog.com/en/tokyo/A1319/A131901/13318587/) |",
        "| らぁめん4区 | つけ麺 | 東中野のつけ麺専門店、2026年2月開店 | 食べログ3.08 | [食べログ](https://tabelog.com/tokyo/A1319/A131901/13319386/) |",
    ]),
    (f"{BASE}/regions/tokyo/14_nakano.md", "中野坂上駅（東京メトロ丸ノ内線", [
        "| 中華そば 千波 | 背脂中華そば | 「らぁ麺 なとり」跡地、焼きあご香る背脂中華そば・量調整可、2026年3月開店 | 食べログ3.09 | [食べログ](https://tabelog.com/tokyo/A1319/A131903/13320103/) |",
    ]),
    (f"{BASE}/regions/tokyo/14_nakano.md", "中野新橋駅（東京メトロ丸ノ内線", [
        "| 背脂煮干新潟中華そば 我武者羅 | ラーメン（新潟系・背脂煮干） | 背脂煮干しの新潟系中華そば、2026年2月開店 | 食べログ3.08 | [食べログ](https://tabelog.com/tokyo/A1319/A131903/13319482/) |",
    ]),
    # 杉並区
    (f"{BASE}/regions/tokyo/15_suginami.md", "阿佐ケ谷駅（JR中央・総武線）", [
        "| 麦と手 | 台湾まぜそば（手打ち極太麺） | 高円寺「混ぜそば みなみ」2号店、ゴワゴワ手打ち自家製麺、2026年1月開店 | 食べログ3.37 | [食べログ](https://tabelog.com/en/tokyo/A1319/A131905/13318205/) |",
        "| 阿佐ヶ谷 わんたん亭 | ラーメン（わんたん麺） | 阿佐ヶ谷のわんたん麺新店、2026年1月開店 | 食べログ3.18 | [食べログ](https://tabelog.com/tokyo/A1319/A131905/13318248/) |",
    ]),
    (f"{BASE}/regions/tokyo/15_suginami.md", "高円寺駅（JR中央・総武線）", [
        "| 花木流味噌 高円寺店 | ラーメン・つけ麺・油そば（味噌） | 味噌専門の新店舗、2026年5月開店 | 点数未確定（新店） | [食べログ](https://tabelog.com/tokyo/A1319/A131905/13322813/) |",
    ]),
    # 豊島区
    (f"{BASE}/regions/tokyo/16_toshima.md", "池袋駅（JR各線", [
        "| みそきん 池袋店 | 味噌ラーメン（完全予約制） | HIKAKIN監修・東京ラーメンストリート店閉店後の新店舗、完全予約制、2026年3月開店 | 食べログ3.32 | [食べログ](https://tabelog.com/en/tokyo/A1305/A130501/13319902/) |",
        "| わいず一門 池袋ラーメン 梟 | 家系ラーメン（濃厚豚骨醤油） | 神田「ラーメンわいず」プロデュース、吊るし焼きチャーシュー・連日行列、2026年2月開店 | 点数未確定（新店） | [池袋タイムズ](https://ikebukuro-times.com/archives/fukuro-ramen20260227.html) |",
    ]),
    (f"{BASE}/regions/tokyo/16_toshima.md", "東長崎駅（西武池袋線）", [
        "| 麺彩RASEN | ラーメン | 東長崎の新店、2026年4月開店 | 食べログ3.07 | [食べログ](https://tabelog.com/tokyo/A1316/A131606/13321248/) |",
    ]),
    # 北区
    (f"{BASE}/regions/tokyo/17_kita.md", "赤羽駅（JR京浜東北", [
        "| 麺処 にぼし香 赤羽店 | 濃厚煮干蕎麦・つけ麺 | 「丿貫(へちかん)」出身、煮干蕎麦＋あさりガリバタ和え玉、2026年2月開店 | 食べログ3.36 | [赤羽マガジン](https://akabane-shinbun.com/archives/235159) |",
    ]),
    # 荒川区
    (f"{BASE}/regions/tokyo/18_arakawa.md", "西日暮里駅（JR山手", [
        "| 深だし煮干し中華そば ばつぐん | 煮干し中華そば・つけそば | 「深だしとろろメシ」が評判・前店「伊蔵八本店」から業態変更、2026年4月開店 | 食べログ3.20 | [荒川ストーリー](https://arakawa-story.com/?p=19299) |",
        "| ビーフヌードル 丑の上にも三年 | ビーフヌードル（特製テール塩そば） | 「今日の1番」3rdブランドの東京初進出、月曜定休、2026年5月開店 | 食べログ3.04 | [荒川102](https://arakawa102.com/food/ushinouenimo3year/) |",
    ]),
    (f"{BASE}/regions/tokyo/18_arakawa.md", "町屋駅（千代田線）", [
        "| まぜまぜ怪獣 町屋店 | 油そば専門 | 「餃子工房ゆうき屋」跡地、2026年5月開店 | 食べログ3.06 | [荒川102](https://arakawa102.com/category/%E9%96%8B%E5%BA%97%E9%96%89%E5%BA%97/) |",
    ]),
    # 板橋区
    (f"{BASE}/regions/tokyo/19_itabashi.md", "大山駅（東武東上線）", [
        "| 元祖まぐろラーメン 大山店 | 油そば・まぜそば（まぐろ出汁） | 1993年創業・環七名店の2号店、まぐろ出汁の油そばが看板、初日40%引き、2026年4月開店 | 食べログ3.05 | [板橋タイムズ](https://itabashi-times.com/archives/maguro-ramen20260427.html) |",
    ]),
    (f"{BASE}/regions/tokyo/19_itabashi.md", "ときわ台駅（東武東上線）", [
        "| 中華そば なみ汐 | 中華そば | ときわ台の中華そば新店、2026年4月開店 | 食べログ3.07 | [食べログ](https://tabelog.com/tokyo/A1320/A132001/13321183/) |",
    ]),
    (f"{BASE}/regions/tokyo/19_itabashi.md", "東武練馬駅（板橋区側）", [
        "| 油そばBEEF-MEN Noodle&Rice | 油そば・まぜそば（牛系） | 牛系油そばの新店、2026年1月開店 | 食べログ3.09 | [食べログ](https://tabelog.com/tokyo/A1320/A132001/13317914/) |",
    ]),
    # 練馬区
    (f"{BASE}/regions/tokyo/20_nerima.md", "練馬駅（都営大江戸線）", [
        "| 鶏之諺 TOKYO01 | 鶏白湯ラーメン・つけ麺 | 大阪・梅田の人気店の関東初進出、濃厚クリーミー鶏白湯・トリュフ香る特製も、2026年3月開店 | 食べログ3.15 | [食べログ](https://tabelog.com/tokyo/A1321/A132102/13319354/) |",
    ]),
    # 足立区
    (f"{BASE}/regions/tokyo/21_adachi.md", "梅島駅・五反野駅（東武スカイツリーライン）", [
        "| ラーメン 山太郎 | 二郎系（ヤサイ盛・自家製麺） | 「花木流味噌 五反野店」跡地、2026年5月開店 | 点数未確定（新店） | [実食ブログ](https://volumey.hatenablog.com/entry/2026/05/11/222736) |",
    ]),
]

# New section to add in 21_adachi.md before 青井駅・六町駅
NEW_SECTION_ADACHI = [
    "### 江北駅（日暮里・舎人ライナー）",
    "| 店名 | ジャンル | 看板・特徴 | 評価の目安 | 出典 |",
    "|---|---|---|---|---|",
    "| 麺舗十六 足立江北店 | つけ麺・ラーメン | 要町の名店（TRYつけ麺部門常連）の2号店、「美楽中華軒」跡地、2026年5月開店 | 点数未確定（新店） | [麺好いブログ](https://ikemen3.blog.jp/archives/1083531763.html) |",
    "",
]

if __name__ == "__main__":
    errors = 0
    for file_path, heading, rows in INSERTIONS:
        if not add_rows(file_path, heading, rows):
            errors += 1
    add_section_before(
        f"{BASE}/regions/tokyo/21_adachi.md",
        "青井駅・六町駅",
        NEW_SECTION_ADACHI,
    )
    print(f"\nDone. Errors: {errors}")
