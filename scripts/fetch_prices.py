# -*- coding: utf-8 -*-
"""심평원 약가기준정보조회서비스(dgamtCrtrInfoService1.2/getDgamtList) 전 품목 수집 → _rawdata/prices.json.
이 API 는 검색어(itmNm 부분일치)가 있어야 결과를 주므로 흔한 음절·제형어로 훑어 합집합(mdsCd 기준)을 만들고,
새 품목이 거의 안 나올 때까지 음절을 늘린다.  키: DATA_GO_KR_API_KEY 또는 ../hosppass/.env 의 API_KEY (로컬 전용).
사용: python scripts/fetch_prices.py"""
import os, sys, re, json, time, collections, pathlib
import requests
sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "_rawdata" / "prices.json"
CACHE = ROOT / "_rawdata" / "cache_prices"
CACHE.mkdir(parents=True, exist_ok=True)
URL = "https://apis.data.go.kr/B551182/dgamtCrtrInfoService1.2/getDgamtList"
S = requests.Session()

def key():
    k = os.environ.get("DATA_GO_KR_API_KEY")
    if k: return k
    for l in open(ROOT.parent / "hosppass" / ".env", encoding="utf-8"):
        if l.startswith("API_KEY"): return l.split("=", 1)[1].strip()
    raise SystemExit("API 키 없음")
K = key()

def parse(t):
    return [dict(re.findall(r"<(\w+)>(.*?)</\1>", it)) for it in re.findall(r"<item>(.*?)</item>", t, re.S)]

def fetch_term(term, per=1000):
    cf = CACHE / (term.encode("utf-8").hex() + ".json")
    if cf.exists(): return json.loads(cf.read_text(encoding="utf-8"))
    rows, p, total = [], 1, None
    while True:
        for attempt in range(6):
            try:
                r = S.get(URL, params=dict(serviceKey=K, pageNo=p, numOfRows=per, itmNm=term), timeout=90)
                t = r.text
                if "<resultCode>00" not in t: raise RuntimeError(t[:150])
                break
            except Exception as e:
                print("retry", term, p, attempt, str(e)[:60], flush=True); time.sleep(2 + attempt * 3)
        else:
            raise SystemExit("실패 " + term)
        if total is None: total = int(re.search(r"<totalCount>(\d+)", t).group(1))
        its = parse(t)
        rows += its
        if not its or len(rows) >= total: break
        p += 1
    cf.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows

def main():
    allr = {}
    def add(rows):
        n = 0
        for d in rows:
            m = d.get("mdsCd")
            if m and m not in allr: allr[m] = d; n += 1
        return n
    seeds = ["정", "캡슐", "주", "액", "산", "연고", "크림", "겔", "시럽", "과립", "패취", "좌", "필름", "점안", "점비", "흡입", "현탁", "분말", "환", "엑스", "스프레이", "로션", "폼", "프리필드", "밀리그램", "밀리리터", "그램", "마이크로", "국제단위", "이", "아", "에", "오", "인", "트", "리", "라", "나", "다", "가", "사", "자", "카", "타", "파", "하", "마", "바", "세", "시", "미", "비", "디", "제", "코", "페", "프", "펜", "신", "메", "스", "큐", "플", "렉", "닌", "론", "린", "민", "빈", "졸", "릴", "틴", "딘", "토", "로", "모", "노", "도", "조", "소", "보", "고", "구", "수", "우", "누", "두", "무", "부", "주사", "용", "성", "복", "서", "대", "한", "동", "유"]
    done = set()
    for t in seeds:
        n = add(fetch_term(t)); done.add(t)
        print(t, "신규", n, "누적", len(allr), flush=True)
    # 누적 품목명에서 많이 쓰이는 음절을 더 훑어 포화시킨다
    for rnd in range(3):
        cnt = collections.Counter()
        for d in allr.values():
            for ch in set(d.get("itmNm", "")):
                if "가" <= ch <= "힣" and ch not in done: cnt[ch] += 1
        new_terms = [c for c, v in cnt.most_common(120)]
        if not new_terms: break
        gain = 0
        for t in new_terms:
            n = add(fetch_term(t)); done.add(t); gain += n
        print("라운드", rnd, "신규 합", gain, "누적", len(allr), flush=True)
        if gain < 30: break
    OUT.write_text(json.dumps(list(allr.values()), ensure_ascii=False), encoding="utf-8")
    print("저장", len(allr), OUT.stat().st_size // 1024, "KB")

if __name__ == "__main__":
    main()
