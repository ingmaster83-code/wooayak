# -*- coding: utf-8 -*-
"""약가(건강보험 급여 상한금액) 비교 페이지 생성 → wooayak/price/ (Jekyll 이 정적 파일로 복사), 사이트맵, 우아약 약 페이지 연결용 _rawdata/drug_prices.json.
입력: _rawdata/prices.json(fetch_prices.py), _rawdata/ingredients.json(fetch_ingredients.py), _rawdata/drugs.json
사용: python scripts/build_price_site.py   (배포 워크플로가 Jekyll 빌드 전에 실행)"""
import sys, json, re, html, shutil, statistics, collections, pathlib, time, urllib.parse
sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "_rawdata"
OUT = ROOT / "price"
BASE = "https://wooayak.wooahouse.com"
esc = html.escape

# ───────────────────────── 서식 ─────────────────────────
def won(x): return "{:,}".format(int(round(x)))
def q(p): return urllib.parse.quote(p, safe="/-_.~()")

def slugify(s, limit=60):
    s = re.sub(r'[\\/?#%&"<>|:*\'`~!@$^+=,;\[\]{}()·]', " ", s)
    s = re.sub(r"\s+", "-", s.strip()).strip(".-")
    return s[:limit].rstrip("-") or "x"

def norm_name(n):
    n = re.sub(r"\(.*", "", n)
    return n.replace("밀리그람", "밀리그램").replace("마이크로그람", "마이크로그램").replace(" ", "").strip()

def split_name(full):
    """'브랜드(성분)_(규격)' → (brand, ingredient, spec)"""
    spec = ""
    i = full.rfind("_(")
    head = full
    if i > 0 and full.endswith(")"):
        spec = full[i + 2:-1]; head = full[:i]
    ingr = ""; brand = head
    if head.endswith(")"):
        depth = 0
        for j in range(len(head) - 1, -1, -1):
            if head[j] == ")": depth += 1
            elif head[j] == "(":
                depth -= 1
                if depth == 0:
                    ingr = head[j + 1:-1]; brand = head[:j]; break
    return brand.strip() or full, ingr.strip(), spec.strip()

def ymd(s): return "%s년 %d월 %d일" % (s[:4], int(s[4:6]), int(s[6:])) if s and len(s) == 8 else ""

def table(heads, rows, num=()):
    th = "".join('<th%s>%s</th>' % (' class="num"' if i in num else "", h) for i, h in enumerate(heads))
    body = "".join("<tr>%s</tr>" % "".join('<td%s>%s</td>' % (' class="num"' if i in num else "", v) for i, v in enumerate(r)) for r in rows)
    return '<div class="tbl-wrap"><table class="ptbl"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (th, body)

ROBOTS = '<meta name="robots" content="noindex,follow">'
AD = ('<div class="ad-slot"><ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-6464921081676309" data-ad-slot="7080296704" '
      'data-ad-format="auto" data-full-width-responsive="true"></ins><script>(adsbygoogle = window.adsbygoogle || []).push({});</script></div>')
COUPANG = ('<div class="coupang-partners" style="margin:36px auto 0;max-width:720px;padding:0 16px 8px;text-align:center;overflow-x:auto;">'
           '<script src="https://ads-partners.coupang.com/g.js"></script>'
           '<script>new PartnersCoupang.G({"id":980427,"trackingCode":"AF5600192","subId":"yak","template":"carousel","width":"680","height":"140"});</script></div>')
CNOTE = '<p style="margin:6px 0 0;font-size:.7rem;opacity:.55;">이 페이지는 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p>'

_JOSA = re.compile(r'(\S)((?:</[a-z]+>)*)(이\(가\)|은\(는\)|을\(를\)|과\(와\))')
_DIG = {"0": True, "1": True, "2": False, "3": True, "4": False, "5": False, "6": True, "7": True, "8": True, "9": False}
def _has_batchim(s, end):
    c = s[end]
    if c == ")":
        k = s.rfind("(", 0, end)
        return _has_batchim(s, k - 1) if k > 0 else False
    if c in _DIG: return _DIG[c]
    if "가" <= c <= "힣": return (ord(c) - 0xAC00) % 28 != 0
    if c.isascii() and c.isalpha(): return c in "lmnrLMNR"
    return False
def josa(t):
    def f(m):
        pair = m.group(3)
        return m.group(1) + m.group(2) + (pair[0] if _has_batchim(m.string, m.start(1)) else pair[2])
    return _JOSA.sub(f, t)

def layout(path, title, desc, body, faq=None, crumbs=None, coupang=False, noindex=False):
    canon = BASE + q(path)
    title, desc, body = josa(title), josa(desc), josa(body)
    if faq: faq = [(josa(a), josa(b)) for a, b in faq]
    ld = []
    if crumbs:
        ld.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": BASE + q(u)} for i, (n, u) in enumerate(crumbs)]})
    if faq:
        ld.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": a, "acceptedAnswer": {"@type": "Answer", "text": b}} for a, b in faq]})
    ld_html = "".join('<script type="application/ld+json">%s</script>' % json.dumps(x, ensure_ascii=False).replace("</", "<\\/") for x in ld)
    crumb = ""
    if crumbs:
        crumb = '<nav class="breadcrumb" aria-label="위치">' + " <span>›</span> ".join(
            ('<a href="%s">%s</a>' % (u, esc(n))) if i < len(crumbs) - 1 else "<span>%s</span>" % esc(n) for i, (n, u) in enumerate(crumbs)) + "</nav>"
    faq_html = ""
    if faq:
        faq_html = '<div class="faq-block"><h2>자주 묻는 질문</h2>' + "".join('<details><summary>%s</summary><p>%s</p></details>' % (esc(a), esc(b)) for a, b in faq) + "</div>"
    full_title = "%s | 이약뭐야?" % title
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canon}">
{ROBOTS if noindex else ""}
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{BASE}/assets/og-image.png">
<meta property="og:url" content="{canon}">
<meta property="og:site_name" content="이약뭐야?">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/css/main.css">
<link rel="stylesheet" href="/assets/css/price.css?v=1">
<meta name="naver-site-verification" content="d965ce24e7a2e9a3cb5780722cd5b67495870b4b" />
<meta name="google-site-verification" content="hd_ljwKChJ8jgoXhqiAHgTM-LrR2rNfOKRHEuHf6Lrk" />
<script async src="https://www.googletagmanager.com/gtag/js?id=G-9ZGENFSXWC"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-9ZGENFSXWC');</script>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6464921081676309" crossorigin="anonymous"></script>
{ld_html}
</head>
<body>
<header class="site-header"><div class="header-inner">
<a href="/" class="site-logo"><span class="logo-icon">💊</span><span class="logo-text">이약뭐야?</span></a>
<nav class="header-nav"><a href="/">의약품 검색</a><a href="/price/">약 가격 비교</a><a href="/identify/">알약 역검색</a><a href="https://wooahouse.com" target="_blank" rel="noopener">WooaHouse →</a></nav>
</div></header>
<script src="/assets/js/wooa-sites-bar.js"></script>
<script src="/assets/js/ad-dev-placeholder.js"></script>
<main class="site-main"><div class="price-page">
{crumb}
{body}
{faq_html}
</div></main>
{COUPANG if coupang else ""}
<footer class="site-footer"><div class="footer-inner">
<p>약 가격은 건강보험심사평가원 「약가기준정보조회서비스」(공공데이터포털, 공공누리 제1유형)의 건강보험 급여 상한금액이며 실제 약국 판매가·본인부담금과 다를 수 있습니다. 의약품 정보는 식품의약품안전처 공공데이터를 기반으로 하며 복약은 반드시 의사·약사와 상담하세요.</p>
<p class="footer-links"><a href="https://wooahouse.com" target="_blank">WooaHouse</a> · <a href="/price/">약 가격 비교</a> · <a href="/privacy/">개인정보처리방침</a></p>
<p class="copyright">&copy; 2026 이약뭐야? · WooaHouse. All rights reserved.</p>
{CNOTE if coupang else ""}
</div></footer>
</body>
</html>
"""

WRITTEN = []
def write(path, text, prio="0.6", sitemap=True):
    f = OUT.parent / path.strip("/") / "index.html"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")
    if sitemap: WRITTEN.append((path, prio))

# ───────────────────────── 데이터 ─────────────────────────
def load():
    src = RAW / "prices_active.json" if (RAW / "prices_active.json").exists() else RAW / "prices.json"
    prices = json.load(open(src, encoding="utf-8"))
    ing = json.load(open(RAW / "ingredients.json", encoding="utf-8")) if (RAW / "ingredients.json").exists() else {}
    prods = []
    for x in prices:
        if x.get("payTpNm") != "급여": continue
        try: pr = float(x.get("mxCprc") or 0)
        except Exception: pr = 0
        if pr <= 0: continue
        brand, ingr, spec = split_name(x["itmNm"])
        prods.append(dict(id=x["mdsCd"], full=x["itmNm"], brand=brand, ingr=ingr, spec=spec, maker=x.get("mnfEntpNm", "").strip(), price=pr,
                          unit=x.get("unit", ""), typ=x.get("spcGnlTpNm", ""), route=x.get("injcPthNm", ""), gcode=x.get("gnlNmCd", ""),
                          mef=x.get("meftDivNo", ""), date=x.get("adtStaDd", ""), sub=x.get("sbstPsblTpNm", "")))
    return prods, ing

def price_txt(p):
    return ("%s원" % won(p["price"])) if p["price"] >= 10 or float(p["price"]).is_integer() else ("%.1f원" % p["price"])

# ───────────────────────── 실행 ─────────────────────────
def main():
    t0 = time.time()
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    prods, ing = load()
    print("급여 품목", len(prods))
    # 슬러그
    used = set()
    for p in prods:
        s = slugify(p["brand"]) + "-" + p["id"].lower()
        p["slug"] = s
    maker_cnt = collections.Counter(p["maker"] for p in prods)
    groups = collections.defaultdict(list)
    for p in prods: groups[p["gcode"]].append(p)
    # 그룹 메타
    G = {}
    for code, lst in groups.items():
        iname = collections.Counter(p["ingr"] for p in lst if p["ingr"]).most_common(1)
        info = ing.get(code) or {}
        ingr_k = iname[0][0] if iname else (info.get("gnlNm") or code)
        content = ""
        if info.get("iqtyTxt"): content = (info["iqtyTxt"] + (info.get("unit") or "")).replace(" ", "")
        form = (info.get("fomnTpCdNm") or "").split(",")[0]
        route = info.get("injcPthCdNm") or (lst[0]["route"] if lst else "")
        title = " ".join(x for x in [ingr_k, content, form] if x)
        G[code] = dict(code=code, ingr=ingr_k, eng=info.get("gnlNm", ""), content=content, form=form, route=route, cls=info.get("divNm", ""), clsno=info.get("meftDivNo", ""),
                       title=title, slug=slugify(ingr_k, 40) + ("-" + slugify(content, 12) if content and len(content) <= 12 else "") + "-" + code.lower(), prods=sorted(lst, key=lambda p: (p["price"], p["brand"])))
    # 우아약 연결 맵
    drugs = json.load(open(RAW / "drugs.json", encoding="utf-8"))
    by_norm = collections.defaultdict(list)
    for p in prods: by_norm[norm_name(p["brand"])].append(p)
    dmap = {}
    for d in drugs:
        k = norm_name(d["itemName"])
        if k in by_norm and k:
            rows = sorted(by_norm[k], key=lambda p: p["price"])[:8]
            dmap[d["itemSeq"]] = [dict(name=r["brand"], spec=r["spec"], price=price_txt(r), unit=r["unit"], maker=r["maker"], slug=r["slug"]) for r in rows]
    (RAW / "drug_prices.json").write_text(json.dumps(dmap, ensure_ascii=False), encoding="utf-8")
    print("우아약 연결", len(dmap))
    drug_slug = {norm_name(d["itemName"]): d["slug"] for d in drugs}

    # ── 제품 페이지 ──
    n_prod = 0
    for p in prods:
        g = G[p["gcode"]]
        gl = g["prods"]
        n = len(gl)
        rank = sum(1 for x in gl if x["price"] < p["price"]) + 1
        low, high = gl[0], gl[-1]
        med = statistics.median(x["price"] for x in gl)
        path = "/price/drug/%s/" % p["slug"]
        pt = price_txt(p)
        unit = p["unit"] or "단위"
        if n >= 2:
            pct = (p["price"] - low["price"]) / low["price"] * 100 if low["price"] else 0
            if p["price"] == low["price"]:
                cmp_txt = "같은 성분·함량의 급여 약 %d개 중 <b>가장 저렴한 약</b>입니다(최고가 %s원, 가격 차이 최대 %.1f배)." % (n, won(high["price"]), high["price"] / low["price"])
            else:
                cmp_txt = "같은 성분·함량의 급여 약 <b>%d개 중 %d번째로 저렴</b>합니다. 최저가는 %s(%s) %s원으로 이 약보다 %.0f%% 낮고, 최고가는 %s원입니다." % (
                    n, rank, esc(low["brand"]), esc(low["maker"]), won(low["price"]), (p["price"] - low["price"]) / p["price"] * 100, won(high["price"]))
        else:
            cmp_txt = "같은 성분·함량의 다른 급여 약은 없습니다."
        # 비교표: 최저가 5 + 이 약 주변
        peers = []
        seen = set()
        for x in gl[:5] + gl[max(0, rank - 4): rank + 4]:
            if x["id"] in seen: continue
            seen.add(x["id"]); peers.append(x)
        peers.sort(key=lambda x: (x["price"], x["brand"]))
        rows = []
        for x in peers[:12]:
            nm = ("<b>%s</b>" % esc(x["brand"])) if x["id"] == p["id"] else '<a href="/price/drug/%s/">%s</a>' % (x["slug"], esc(x["brand"]))
            rows.append([nm, esc(x["maker"]), esc(x["typ"]), price_txt(x)])
        peer_t = table(["제품", "제조사", "구분", "상한금액(1%s)" % esc(unit)], rows, (3,))
        same_m = [x for x in prods if False]
        link_yak = ""
        dk = norm_name(p["brand"])
        if dk in drug_slug: link_yak = '<p class="lead"><a href="/drug/%s/">💊 %s 효능·용법·부작용 보기 →</a></p>' % (drug_slug[dk], esc(p["brand"]))
        typ_txt = {"전문": "의사 처방이 필요한 전문의약품입니다.", "일반": "약국에서 처방 없이 살 수 있는 일반의약품이지만 건강보험 급여 대상으로 등재돼 있습니다."}.get(p["typ"], "")
        body = f"""
<div class="page-head"><h1>{esc(p['brand'])} 가격 — 상한금액 {pt}</h1><p>{esc(p['maker'])} · {esc(p['typ'])}의약품 · {esc(g['title'])}</p></div>
<p class="lead"><b>{esc(p['brand'])}</b>({esc(p['maker'])})의 건강보험 급여 <b>상한금액은 1{esc(unit)}당 {pt}</b>입니다{('(적용일 ' + ymd(p['date']) + ')') if p['date'] else ''}. {typ_txt} {cmp_txt}</p>
<div class="stat-row"><div class="stat"><small>상한금액</small><b>{pt}</b></div><div class="stat"><small>단위</small><b>1{esc(unit)}</b></div><div class="stat"><small>같은 성분 약</small><b>{n}개</b></div><div class="stat"><small>가격 순위</small><b>{rank}위/{n}</b></div></div>
{AD}
<h2 class="group-title">💰 같은 성분·함량 약 가격 비교</h2>
{peer_t}
<p class="lead"><a href="/price/ingredient/{g['slug']}/">{esc(g['title'])} 전체 {n}개 약 가격표 보기 →</a></p>
{link_yak}
<h2 class="group-title">ℹ️ 상세 정보</h2>
{table(['항목', '내용'], [['제품명', esc(p['full'])], ['제조·수입사', esc(p['maker'])], ['성분', esc(p['ingr'] or g['ingr'])], ['규격', esc(p['spec'] or '-')], ['투여경로', esc(p['route'] or '-')], ['약효 분류', esc(g['cls'] or '-')], ['급여 상한금액', pt + ' (1' + esc(unit) + ')'], ['적용일', ymd(p['date']) or '-'], ['약제 코드', esc(p['id'])]])}
<div class="note-box">상한금액은 건강보험이 인정하는 최고 가격이며 약국의 실제 판매가와 환자 본인부담금은 다를 수 있습니다(본인부담률·조제료 등 별도). 같은 성분이라도 의사가 처방한 약을 임의로 바꾸지 말고 약사·의사와 상담하세요.</div>
"""
        faq = [(f"{p['brand']} 가격은 얼마인가요?", f"건강보험 급여 상한금액은 1{unit}당 {pt}입니다. 실제 약국 판매가는 이와 다를 수 있습니다."),
               (f"{p['brand']}보다 싼 같은 성분 약이 있나요?", ("있습니다. 가장 저렴한 약은 %s(%s) %s원입니다." % (low['brand'], low['maker'], won(low['price']))) if p["price"] > low["price"] else "이 약이 같은 성분·함량 급여 약 중 가장 저렴한 가격대입니다." if n >= 2 else "같은 성분·함량의 다른 급여 약이 없습니다."),
               ("상한금액이란 무엇인가요?", "건강보험이 약값으로 인정하는 최고 금액입니다. 약국은 이 금액 이하로 판매·청구하며 환자는 본인부담률에 따라 일부만 냅니다.")]
        write(path, layout(path, f"{p['brand']} 가격 ({pt}) — 같은 성분 약 {n}개 비교" if n >= 2 else f"{p['brand']} 가격 ({pt}) — 건강보험 상한금액",
              f"{p['brand']}({p['maker']}) 건강보험 상한금액 1{unit}당 {pt}. 같은 성분·함량 약 {n}개 중 {rank}번째로 저렴. 제네릭 가격 비교와 대체 가능한 약.", body, faq,
              [("홈", "/"), ("약 가격 비교", "/price/"), (g["ingr"], f"/price/ingredient/{g['slug']}/"), (p["brand"], path)], coupang=(n >= 15), noindex=(n < 2)), "0.5" if n < 15 else "0.6", sitemap=(n >= 2))
        n_prod += 1

    # ── 성분 페이지 ──
    n_g = 0
    for g in G.values():
        gl = g["prods"]
        if len(gl) < 2: continue
        n = len(gl)
        pr = [x["price"] for x in gl]
        med = statistics.median(pr)
        path = "/price/ingredient/%s/" % g["slug"]
        rows = []
        for i, x in enumerate(gl[:250], 1):
            rows.append([str(i), '<a href="/price/drug/%s/">%s</a>' % (x["slug"], esc(x["brand"])), esc(x["maker"]), esc(x["typ"]), price_txt(x)])
        t = table(["순위", "제품", "제조사", "구분", "상한금액(1%s)" % esc(gl[0]["unit"] or "단위")], rows, (0, 4))
        more = "<p class=\"note\">가격이 낮은 순 250개까지 표시했습니다(총 %d개).</p>" % n if n > 250 else ""
        cheap = gl[0]
        body = f"""
<div class="page-head"><h1>{esc(g['title'])} 가격 비교 — 같은 성분 약 {n}개</h1><p>건강보험 급여 상한금액 · {esc(g['cls'] or '의약품')}</p></div>
<p class="lead"><b>{esc(g['title'])}</b>은(는) 건강보험 급여로 등재된 약이 <b>{n}개</b>입니다. 상한금액은 1{esc(gl[0]['unit'] or '단위')}당 <b>{won(pr[0]) if pr[0] >= 10 else pr[0]}원~{won(pr[-1])}원</b>(중앙값 {won(med) if med >= 10 else med}원)이며 가장 비싼 약은 가장 싼 약의 약 {pr[-1] / pr[0]:.1f}배입니다. 가장 저렴한 약은 {esc(cheap['brand'])}({esc(cheap['maker'])})입니다.{(' 영문 성분명은 ' + esc(g['eng']) + '입니다.') if g['eng'] else ''}</p>
<div class="stat-row"><div class="stat"><small>급여 약</small><b>{n}개</b></div><div class="stat"><small>최저</small><b>{won(pr[0]) if pr[0] >= 10 else pr[0]}원</b></div><div class="stat"><small>중앙값</small><b>{won(med) if med >= 10 else med}원</b></div><div class="stat"><small>최고</small><b>{won(pr[-1])}원</b></div></div>
{AD}
{t}
{more}
<div class="note-box">같은 성분·함량이어도 제형·첨가제·제조사에 따라 효과·부작용 경험이 다를 수 있습니다. 처방받은 약을 임의로 바꾸지 말고 의사·약사와 상담하세요. 상한금액은 건강보험 인정 최고금액이며 실제 약국 판매가와 다를 수 있습니다.</div>
{('<div class="chips"><a class="chip" href="/price/class/%s/">%s 약 전체</a></div>' % (g['clsno'], esc(g['cls']))) if g['clsno'] and g['cls'] else ''}
"""
        faq = [(f"{g['title']} 가격은 얼마인가요?", f"건강보험 급여 상한금액 기준 1{gl[0]['unit']}당 {won(pr[0]) if pr[0] >= 10 else pr[0]}원~{won(pr[-1])}원이며 중앙값은 {won(med) if med >= 10 else med}원입니다."),
               (f"{g['title']} 중 가장 저렴한 약은?", f"{cheap['brand']}({cheap['maker']})이 {won(pr[0]) if pr[0] >= 10 else pr[0]}원으로 가장 낮습니다."),
               ("제네릭 약은 오리지널과 같은가요?", "제네릭은 오리지널과 주성분·함량·제형이 같고 생물학적 동등성을 입증한 약입니다. 다만 첨가제가 달라 드물게 반응이 다를 수 있어 의사·약사와 상의해 바꾸는 것이 좋습니다.")]
        write(path, layout(path, f"{g['title']} 가격 비교 — 같은 성분 약 {n}개 ({won(pr[0]) if pr[0] >= 10 else pr[0]}~{won(pr[-1])}원)",
              f"{g['title']} 건강보험 급여 약 {n}개의 상한금액 비교. 최저 {won(pr[0]) if pr[0] >= 10 else pr[0]}원, 최고 {won(pr[-1])}원, 중앙값 {won(med) if med >= 10 else med}원. 제조사별 제네릭 가격표.", body, faq,
              [("홈", "/"), ("약 가격 비교", "/price/"), (g["title"], path)], coupang=(n >= 15)), "0.8" if n >= 10 else "0.7")
        n_g += 1

    # ── 제조사 페이지 ──
    mk = collections.defaultdict(list)
    for p in prods: mk[p["maker"]].append(p)
    n_m = 0
    for m, lst in sorted(mk.items(), key=lambda kv: -len(kv[1])):
        if len(lst) < 20 or not m: continue
        path = "/price/maker/%s/" % slugify(m)
        top = sorted(lst, key=lambda p: -p["price"])[:100]
        gcnt = len({p["gcode"] for p in lst})
        rows = [['<a href="/price/drug/%s/">%s</a>' % (x["slug"], esc(x["brand"])), esc(G[x["gcode"]]["ingr"]), esc(x["typ"]), price_txt(x)] for x in sorted(lst, key=lambda p: p["brand"])[:300]]
        body = f"""
<div class="page-head"><h1>{esc(m)} 약 가격 — 건강보험 급여 {len(lst):,}개 품목</h1><p>성분 {gcnt}종 · 상한금액</p></div>
<p class="lead">{esc(m)}의 건강보험 급여 의약품은 <b>{len(lst):,}개</b> 품목(성분·함량 {gcnt}종)입니다. 제품을 누르면 같은 성분 약과의 가격 비교를 볼 수 있습니다.</p>
{AD}
{table(['제품', '성분', '구분', '상한금액'], rows, (3,))}
{('<p class="note">이름순 300개까지 표시했습니다(총 %d개).</p>' % len(lst)) if len(lst) > 300 else ''}
"""
        write(path, layout(path, f"{m} 약 가격 — 급여 {len(lst):,}개 품목 상한금액", f"{m}의 건강보험 급여 의약품 {len(lst):,}개 품목 상한금액 목록과 같은 성분 약 가격 비교.", body, None,
              [("홈", "/"), ("약 가격 비교", "/price/"), (m, path)]), "0.5")
        n_m += 1

    # ── 약효분류 페이지 ──
    cl = collections.defaultdict(list)
    for g in G.values():
        if g["clsno"] and g["cls"]: cl[(g["clsno"], g["cls"])].append(g)
    n_c = 0
    for (no, name), gs in sorted(cl.items()):
        gs2 = [g for g in gs if len(g["prods"]) >= 2]
        if not gs2: continue
        path = "/price/class/%s/" % no
        rows = [['<a href="/price/ingredient/%s/">%s</a>' % (g["slug"], esc(g["title"])), "%d개" % len(g["prods"]), "%s~%s원" % (won(g["prods"][0]["price"]) if g["prods"][0]["price"] >= 10 else g["prods"][0]["price"], won(g["prods"][-1]["price"]))]
                for g in sorted(gs2, key=lambda g: -len(g["prods"]))[:300]]
        body = f"""
<div class="page-head"><h1>{esc(name)} 약 가격 비교 — 성분 {len(gs2)}종</h1><p>약효 분류 {no}</p></div>
<p class="lead">‘{esc(name)}’ 약효군에서 같은 성분·함량의 급여 약이 2개 이상인 성분 {len(gs2)}종입니다. 성분을 누르면 제조사별 가격표를 볼 수 있습니다.</p>
{AD}
{table(['성분·함량', '급여 약', '상한금액 범위'], rows, (1, 2))}
"""
        write(path, layout(path, f"{name} 약 가격 비교 — 성분별 제네릭 가격", f"{name} 약효군 {len(gs2)}개 성분의 건강보험 급여 약 가격 비교.", body, None, [("홈", "/"), ("약 가격 비교", "/price/"), (name, path)]), "0.5")
        n_c += 1

    # ── 허브·검색 ──
    pop = sorted([g for g in G.values() if len(g["prods"]) >= 2], key=lambda g: -len(g["prods"]))[:40]
    pop_html = "".join('<a class="chip" href="/price/ingredient/%s/">%s</a>' % (g["slug"], esc(g["title"])) for g in pop)
    cls_html = "".join('<a class="chip" href="/price/class/%s/">%s</a>' % (no, esc(name)) for (no, name), gs in sorted(cl.items(), key=lambda kv: -len(kv[1]))[:30])
    mk_html = "".join('<a class="chip" href="/price/maker/%s/">%s</a>' % (slugify(m), esc(m)) for m, lst in sorted(mk.items(), key=lambda kv: -len(kv[1]))[:30] if len(lst) >= 20 and m)
    body = f"""
<div class="page-head"><h1>약 가격 비교 — 건강보험 급여 의약품 상한금액</h1><p>급여 약 {len(prods):,}개 · 비교 가능한 성분 {sum(1 for g in G.values() if len(g["prods"]) >= 2):,}종</p></div>
<div class="hero-search"><input id="pq" type="search" placeholder="약 이름 또는 성분을 입력하세요 (예: 아모디핀, 아토르바스타틴)" autocomplete="off"><div class="sr-list" id="psr"></div></div>
<p class="lead">약 이름이나 성분으로 건강보험 급여 상한금액을 찾고, <b>같은 성분·함량의 제네릭 약과 가격을 비교</b>하세요. 급여 의약품 {len(prods):,}개의 상한금액(1정·1캡슐 등 단위당)을 성분·제조사별로 정리했고, 같은 성분·함량의 약이 2개 이상인 성분 {sum(1 for g in G.values() if len(g["prods"]) >= 2):,}종은 가격표로 비교할 수 있습니다.</p>
{AD}
<h2 class="group-title">🔥 제네릭이 많은 성분</h2>
<div class="chips">{pop_html}</div>
<h2 class="group-title">🧪 약효 분류별</h2>
<div class="chips">{cls_html}</div>
<h2 class="group-title">🏭 제조사별</h2>
<div class="chips">{mk_html}</div>
<div class="note-box">상한금액은 건강보험이 인정하는 최고 가격으로 실제 약국 판매가·본인부담금과 다를 수 있습니다. 일반의약품 대부분은 급여 대상이 아니라 이 목록에 없습니다. 복약은 의사·약사와 상담하세요.</div>
<script src="/assets/js/price-search.js"></script>
"""
    faq = [("약 가격은 어디서 확인하나요?", "이 사이트는 건강보험심사평가원의 약제 급여 상한금액을 보여 줍니다. 약 이름을 검색하면 같은 성분 제네릭과의 가격 차이를 비교할 수 있습니다."),
           ("같은 성분인데 가격이 왜 다른가요?", "오리지널 약과 제네릭 약, 제조사별로 상한금액이 다르게 등재되기 때문입니다. 성분·함량이 같으면 효능은 같지만 첨가제 등이 다를 수 있습니다."),
           ("약국에서 내는 돈과 같은가요?", "상한금액은 건강보험이 인정하는 약값의 최고 금액입니다. 환자는 본인부담률(보통 30% 안팎)과 조제료 등을 포함해 약국에서 결제합니다.")]
    write("/price/", layout("/price/", "약 가격 비교 — 건강보험 급여 약 상한금액·제네릭 가격", "건강보험 급여 의약품 상한금액 조회. 약 이름·성분으로 검색하고 같은 성분 제네릭 가격을 제조사별로 비교하세요.", body, faq, [("홈", "/"), ("약 가격 비교", "/price/")], coupang=True), "0.9")
    sidx = [["p", p["brand"] + (" " + p["spec"] if False else ""), p["maker"], p["price"], p["slug"], p["unit"]] for p in prods]
    sidx += [["g", g["title"], len(g["prods"]), g["slug"]] for g in G.values() if len(g["prods"]) >= 2]
    (OUT / "search.json").write_text(json.dumps(sidx, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    # ── 사이트맵 ──
    today = time.strftime("%Y-%m-%d")
    for n in range(0, len(WRITTEN), 40000):
        ch = WRITTEN[n:n + 40000]
        urls = "".join("<url><loc>%s%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>" % (BASE, q(pth), today, pr) for pth, pr in ch)
        (ROOT / ("sitemap-price-%d.xml" % (n // 40000 + 1))).write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n' % urls, encoding="utf-8")
    print("제품", n_prod, "성분", n_g, "제조사", n_m, "분류", n_c, "총", len(WRITTEN), "elapsed", round(time.time() - t0), "s")

if __name__ == "__main__":
    main()
