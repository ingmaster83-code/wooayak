#!/usr/bin/env python3
"""
fetch_health.py - 식품안전나라 건강기능식품 API 전체 수집
결과를 _rawdata/supplements.json으로 저장
사용법:
  python scripts/fetch_health.py
  python scripts/fetch_health.py --limit 50  # 테스트
"""
import json
import re
import sys
import time
import argparse
from pathlib import Path
import requests

sys.stdout.reconfigure(encoding='utf-8')

API_KEY  = "9fea81760dce4f86ac18"
BASE_URL = "http://openapi.foodsafetykorea.go.kr/api"

OUT_DIR  = Path(__file__).parent.parent / "_data"
OUT_FILE = OUT_DIR / "supplements.json"

BATCH = 100
DELAY = 0.3


def fetch_all(service_id: str, limit: int = 0) -> list:
    items = []
    start = 1

    while True:
        end = start + BATCH - 1
        url = f"{BASE_URL}/{API_KEY}/{service_id}/json/{start}/{end}"

        retry = 0
        data = None
        while retry < 5:
            try:
                r = requests.get(url, timeout=30)
                data = r.json()
                break
            except Exception as e:
                retry += 1
                wait = DELAY * (3 ** retry)
                print(f"  [재시도 {retry}/5] {service_id} start={start}: {e} → {wait:.0f}초 대기")
                time.sleep(wait)

        if data is None:
            print(f"  [포기] {service_id} start={start}")
            break

        svc   = data.get(service_id, {})
        total = int(svc.get("total_count", 0))
        rows  = svc.get("row", [])

        if not rows:
            break
        if isinstance(rows, dict):
            rows = [rows]

        items.extend(rows)
        print(f"  {service_id} | {start}~{end} | 수집 {len(items):5d} / {total}")

        if limit and len(items) >= limit:
            items = items[:limit]
            break
        if len(items) >= total:
            break

        start += BATCH
        time.sleep(DELAY)

    return items


def clean(text) -> str:
    if not text:
        return ""
    text = str(text).strip()
    if text in ("(없음)", "없음", "-", ""):
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    return text.replace("\xa0", " ").strip()


def slugify(name: str) -> str:
    name = re.sub(r"[^\w\s가-힣]", "", name)
    name = re.sub(r"\s+", "-", name.strip())
    return name[:60].strip("-").lower()


def build_supplement(row: dict, source: str) -> dict:
    """I2710(품목분류) 기반 레코드 생성"""
    name = clean(row.get("PRDCT_NM", ""))
    if not name:
        return None

    item_id = clean(row.get("SKLL_IX_IRDNT_RAWMTRL", name))[:30]
    uid = f"sup-{slugify(name)}"

    return {
        "type":           "supplement",
        "uid":            uid,
        "slug":           uid,
        "itemName":       name,
        "rawMaterial":    clean(row.get("SKLL_IX_IRDNT_RAWMTRL", "")),
        "primaryFnclty":  clean(row.get("PRIMARY_FNCLTY", "")),
        "dayIntakeLow":   clean(row.get("DAY_INTK_LOWLIMIT", "")),
        "dayIntakeHigh":  clean(row.get("DAY_INTK_HIGHLIMIT", "")),
        "intakeUnit":     clean(row.get("INTK_UNIT", "")),
        "caution":        clean(row.get("IFTKN_ATNT_MATR_CN", "")),
        "intakeMemo":     clean(row.get("INTK_MEMO", "")),
        "lastUpdate":     clean(row.get("LAST_UPDT_DTM", "")),
        "source":         source,
        "itemImage":      "",
        "entpName":       "",
        "seoDescription": "",
    }


def build_from_i0040(row: dict) -> dict:
    """I-0040(기능성 원료 인정) 기반 레코드"""
    name = clean(row.get("APLC_RAWMTRL_NM", ""))
    if not name:
        return None

    uid = f"sup-{slugify(name)}"
    return {
        "type":           "supplement",
        "uid":            uid,
        "slug":           uid,
        "itemName":       name,
        "rawMaterial":    name,
        "primaryFnclty":  clean(row.get("FNCLTY_CN", "")),
        "dayIntakeLow":   "",
        "dayIntakeHigh":  "",
        "intakeUnit":     clean(row.get("DAY_INTK_CN", "")),
        "caution":        clean(row.get("IFTKN_ATNT_MATR_CN", "")),
        "intakeMemo":     "",
        "lastUpdate":     clean(row.get("PRMS_DT", "")),
        "source":         "I-0040",
        "entpName":       clean(row.get("BSSH_NM", "")),
        "itemImage":      "",
        "seoDescription": "",
    }


def build_from_i0050(row: dict) -> dict:
    """I-0050(개별인정형) 기반 레코드"""
    name = clean(row.get("RAWMTRL_NM", ""))
    if not name:
        return None

    uid = f"sup-{slugify(name)}"
    fnclty = clean(row.get("PRIMARY_FNCLTY", ""))
    # 참고: 원본 필드에 국문/영문 설명이 섞여 있는 경우가 있어
    # 국문 구간만 추출하는 정규식이 있었으나, 원본 인코딩 손상으로
    # 정확한 패턴을 복원할 수 없어 여기서는 원문 그대로 사용한다.

    return {
        "type":           "supplement",
        "uid":            uid,
        "slug":           uid,
        "itemName":       name,
        "rawMaterial":    name,
        "primaryFnclty":  fnclty,
        "dayIntakeLow":   clean(row.get("DAY_INTK_LOWLIMIT", "")),
        "dayIntakeHigh":  clean(row.get("DAY_INTK_HIGHLIMIT", "")),
        "intakeUnit":     clean(row.get("WT_UNIT", "")),
        "caution":        clean(row.get("IFTKN_ATNT_MATR_CN", "")),
        "intakeMemo":     "",
        "lastUpdate":     "",
        "source":         "I-0050",
        "entpName":       "",
        "itemImage":      "",
        "seoDescription": "",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    supplements = {}  # slug → record (중복 제거)

    # ── Step 1: I2710 품목분류 (메인) ──
    print("\n[Step 1] I2710 품목분류정보 수집...")
    rows = fetch_all("I2710", args.limit)
    for row in rows:
        rec = build_supplement(row, "I2710")
        if rec and rec["slug"] not in supplements:
            supplements[rec["slug"]] = rec
    print(f"  → {len(supplements)}건 등록\n")

    # ── Step 2: I-0040 기능성 원료 인정 ──
    print("[Step 2] I-0040 기능성 원료 인정현황 수집...")
    rows = fetch_all("I-0040", args.limit)
    added = 0
    for row in rows:
        rec = build_from_i0040(row)
        if rec and rec["slug"] not in supplements:
            supplements[rec["slug"]] = rec
            added += 1
        elif rec and rec["slug"] in supplements:
            # 기존 레코드에 기능성 보완
            existing = supplements[rec["slug"]]
            if not existing["primaryFnclty"] and rec["primaryFnclty"]:
                existing["primaryFnclty"] = rec["primaryFnclty"]
            if not existing["caution"] and rec["caution"]:
                existing["caution"] = rec["caution"]
    print(f"  → {added}건 신규 추가, 총 {len(supplements)}건\n")

    # ── Step 3: I-0050 개별인정형 ──
    print("[Step 3] I-0050 개별인정형 정보 수집...")
    rows = fetch_all("I-0050", args.limit)
    added = 0
    for row in rows:
        rec = build_from_i0050(row)
        if rec and rec["slug"] not in supplements:
            supplements[rec["slug"]] = rec
            added += 1
    print(f"  → {added}건 신규 추가, 총 {len(supplements)}건\n")

    # ── Step 4: 저장 ──
    result = list(supplements.values())
    # 기능성 정보 없는 항목 제거
    result = [r for r in result if r["primaryFnclty"] or r["rawMaterial"]]

    if OUT_FILE.exists():
        existing = json.loads(OUT_FILE.read_text(encoding="utf-8"))
        if len(result) < len(existing) * 0.5:
            raise SystemExit(
                f"수집 건수({len(result)}건)가 기존 데이터({len(existing)}건)의 절반 미만입니다. "
                "API 오류로 판단하여 저장을 중단합니다."
            )

    OUT_FILE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"[완료] {OUT_FILE}")
    print(f"  총 {len(result)}개 건강기능식품 저장")
    print(f"  파일 크기: {OUT_FILE.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
