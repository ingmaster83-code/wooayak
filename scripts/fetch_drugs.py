#!/usr/bin/env python3
"""
fetch_drugs.py - 식약처 API 전체 데이터 수집 후 _data/drugs.json 생성

수집 대상:
  1. e약은요 API (DrbEasyDrugInfoService) - 효능/용법/주의사항 등
  2. 낱알식별 API (MdcinGrnIdntfcInfoService03) - 모양/색상/이미지 등

JOIN 키: itemSeq (e약은요) == ITEM_SEQ (낱알식별)

사용법:
  python scripts/fetch_drugs.py
  python scripts/fetch_drugs.py --limit 100   # 테스트용 100건만
"""

import json
import time
import argparse
import re
from pathlib import Path
import requests

API_KEY       = "9490b1d34e92aa9e25b32a4cff1438fc7b9c71e5d332413916a391e867f61e86"
EASY_DRUG_URL = "http://apis.data.go.kr/1471000/DrbEasyDrugInfoService/getDrbEasyDrugList"
GRAIN_URL     = "http://apis.data.go.kr/1471000/MdcinGrnIdntfcInfoService03/getMdcinGrnIdntfcInfoList03"

OUT_DIR  = Path(__file__).parent.parent / "_data"
OUT_FILE = OUT_DIR / "drugs.json"

BATCH = 100   # 1회 요청당 건수 (API 최대 100)
DELAY = 0.3   # 요청 간격(초)


def fetch_all(url: str, extra_params: dict = None, limit: int = 0) -> list:
    """페이지네이션으로 전체 데이터 수집"""
    items = []
    page  = 1

    while True:
        params = {
            "serviceKey": API_KEY,
            "type":       "json",
            "numOfRows":  BATCH,
            "pageNo":     page,
        }
        if extra_params:
            params.update(extra_params)

        retry = 0
        while retry < 5:
            try:
                resp = requests.get(url, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                break
            except Exception as e:
                retry += 1
                wait = DELAY * (3 ** retry)
                print(f"  [재시도 {retry}/5] page={page}: {e} → {wait:.0f}초 대기")
                time.sleep(wait)
        else:
            print(f"  [포기] page={page} 5회 실패, 다음으로 진행")
            break

        body = data.get("body", {})
        page_items = body.get("items", [])

        if not page_items:
            break

        # 리스트가 아닌 경우(단일 dict) 처리
        if isinstance(page_items, dict):
            page_items = [page_items]

        items.extend(page_items)

        total = int(body.get("totalCount", 0))
        print(f"  page {page:3d} | 수집 {len(items):5d} / {total}")

        if limit and len(items) >= limit:
            items = items[:limit]
            break

        if len(items) >= total:
            break

        page += 1
        time.sleep(DELAY)

    return items


def clean_text(text) -> str:
    """불필요한 공백·태그 제거"""
    if not text or str(text).strip() in ("(없음)", "없음", ""):
        return ""
    text = str(text)
    # 간단한 HTML 태그 제거
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("\xa0", " ").strip()
    return text


def slugify(name: str) -> str:
    """제품명을 URL-safe slug로 변환"""
    # 한글·영숫자·하이픈만 허용
    name = re.sub(r"[^\w\s가-힣]", "", name)
    name = re.sub(r"\s+", "-", name.strip())
    return name[:60].strip("-").lower()


def build_drug_record(easy: dict, grain: dict = None) -> dict:
    """e약은요 + 낱알식별 데이터를 하나의 레코드로 합치기"""
    item_seq  = str(easy.get("itemSeq", ""))
    item_name = clean_text(easy.get("itemName", ""))

    record = {
        "itemSeq":           item_seq,
        "slug":              f"{item_seq}-{slugify(item_name)}",
        "itemName":          item_name,
        "entpName":          clean_text(easy.get("entpName", "")),
        "efcyQesitm":        clean_text(easy.get("efcyQesitm", "")),
        "useMethodQesitm":   clean_text(easy.get("useMethodQesitm", "")),
        "atpnWarnQesitm":    clean_text(easy.get("atpnWarnQesitm", "")),
        "atpnQesitm":        clean_text(easy.get("atpnQesitm", "")),
        "intrcQesitm":       clean_text(easy.get("intrcQesitm", "")),
        "seQesitm":          clean_text(easy.get("seQesitm", "")),
        "depositMethodQesitm": clean_text(easy.get("depositMethodQesitm", "")),
        "itemImage":         clean_text(easy.get("itemImage", "")),
        "bizrno":            clean_text(easy.get("bizrno", "")),
        # 낱알식별 (없으면 빈값)
        "drugShape":         "",
        "colorClass1":       "",
        "colorClass2":       "",
        "formCodeName":      "",
        "printFront":        "",
        "printBack":         "",
        "lineFront":         "",
        "lineBack":          "",
        "lengLong":          "",
        "lengShort":         "",
        "thick":             "",
        "chart":             "",
        # SEO용 (generate_seo.py에서 채움)
        "seoDescription":    "",
    }

    if grain:
        record.update({
            "drugShape":    clean_text(grain.get("DRUG_SHAPE", "")),
            "colorClass1":  clean_text(grain.get("COLOR_CLASS1", "")),
            "colorClass2":  clean_text(grain.get("COLOR_CLASS2", "")),
            "formCodeName": clean_text(grain.get("FORM_CODE_NAME", "")),
            "printFront":   clean_text(grain.get("PRINT_FRONT", "")),
            "printBack":    clean_text(grain.get("PRINT_BACK", "")),
            "lineFront":    clean_text(grain.get("LINE_FRONT", "")),
            "lineBack":     clean_text(grain.get("LINE_BACK", "")),
            "lengLong":     clean_text(grain.get("LENG_LONG", "")),
            "lengShort":    clean_text(grain.get("LENG_SHORT", "")),
            "thick":        clean_text(grain.get("THICK", "")),
            "chart":        clean_text(grain.get("CHART", "")),
            # 낱알 이미지가 있으면 우선 사용
            "itemImage":    clean_text(grain.get("ITEM_IMAGE", "")) or record["itemImage"],
        })

    return record


def main():
    parser = argparse.ArgumentParser(description="식약처 API 전체 수집")
    parser.add_argument("--limit", type=int, default=0, help="테스트용 건수 제한 (0=전체)")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Step 1: e약은요 전체 수집 ──────────────────────────────
    print("\n[Step 1] e약은요 API 수집 중...")
    easy_items = fetch_all(EASY_DRUG_URL, limit=args.limit)
    print(f"  → 총 {len(easy_items)}건 수집 완료\n")

    # itemSeq → easy dict 인덱스
    easy_index = {str(item.get("itemSeq", "")): item for item in easy_items}

    # ── Step 2: 낱알식별 전체 수집 ────────────────────────────
    print("[Step 2] 낱알식별 API 수집 중...")
    grain_items = fetch_all(GRAIN_URL, limit=0)  # 낱알은 항상 전체
    print(f"  → 총 {len(grain_items)}건 수집 완료\n")

    # ITEM_SEQ → grain dict 인덱스
    grain_index = {str(item.get("ITEM_SEQ", "")): item for item in grain_items}

    # ── Step 3: JOIN 및 레코드 생성 ───────────────────────────
    print("[Step 3] 데이터 병합 중...")
    drugs = []
    matched = 0
    for seq, easy in easy_index.items():
        grain = grain_index.get(seq)
        if grain:
            matched += 1
        record = build_drug_record(easy, grain)
        drugs.append(record)

    print(f"  → 낱알식별 매칭: {matched} / {len(drugs)}건")

    # ── Step 4: 저장 ──────────────────────────────────────────
    OUT_FILE.write_text(
        json.dumps(drugs, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\n[완료] {OUT_FILE}")
    print(f"  총 {len(drugs)}개 약품 저장")
    print(f"  파일 크기: {OUT_FILE.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
