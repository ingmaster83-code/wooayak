# -*- coding: utf-8 -*-
"""약가 데이터의 성분코드(gnlNmCd)별 성분명·함량·제형·약효분류명을 심평원 의약품성분약효정보(msupCmpnMeftInfoService/getMajorCmpnNmCdList)에서 수집 → _rawdata/ingredients.json.
사용: python scripts/fetch_ingredients.py  (개발계정 일일 호출 한도 10,000건 주의: 코드 약 4천 개)"""
import os, sys, re, json, time, pathlib
import requests
sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "_rawdata"
OUT = RAW / "ingredients.json"
URL = "https://apis.data.go.kr/B551182/msupCmpnMeftInfoService/getMajorCmpnNmCdList"

def key():
    k = os.environ.get("DATA_GO_KR_API_KEY")
    if k: return k
    for l in open(ROOT.parent / "hosppass" / ".env", encoding="utf-8"):
        if l.startswith("API_KEY"): return l.split("=", 1)[1].strip()
    raise SystemExit("API 키 없음")

def main():
    K = key()
    prices = json.load(open(RAW / "prices.json", encoding="utf-8"))
    codes = sorted({p["gnlNmCd"] for p in prices if p.get("payTpNm") == "급여" and p.get("gnlNmCd")})
    have = json.load(open(OUT, encoding="utf-8")) if OUT.exists() else {}
    print("codes", len(codes), "have", len(have))
    S = requests.Session()
    n = 0
    for c in codes:
        if c in have: continue
        for attempt in range(5):
            try:
                r = S.get(URL, params=dict(serviceKey=K, pageNo=1, numOfRows=5, gnlNmCd=c), timeout=40)
                t = r.text
                if "<resultCode>00" not in t: raise RuntimeError(t[:120])
                break
            except Exception as e:
                print("retry", c, attempt, str(e)[:60], flush=True); time.sleep(2 + attempt * 2)
        else:
            continue
        its = [dict(re.findall(r"<(\w+)>(.*?)</\1>", it)) for it in re.findall(r"<item>(.*?)</item>", t, re.S)]
        have[c] = its[0] if its else {}
        n += 1
        if n % 300 == 0:
            OUT.write_text(json.dumps(have, ensure_ascii=False), encoding="utf-8"); print(" ", n, flush=True)
    OUT.write_text(json.dumps(have, ensure_ascii=False), encoding="utf-8")
    print("done", len(have), sum(1 for v in have.values() if v))

if __name__ == "__main__":
    main()
