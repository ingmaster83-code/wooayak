#!/usr/bin/env python3
"""
식약처 API 테스트 스크립트
- e약은요 API (DrbEasyDrugInfoService)
- 낱알식별 API (MdcinGrnIdntfcInfoService03)
"""
import json
import requests

API_KEY = "9490b1d34e92aa9e25b32a4cff1438fc7b9c71e5d332413916a391e867f61e86"

EASY_DRUG_URL = "http://apis.data.go.kr/1471000/DrbEasyDrugInfoService/getDrbEasyDrugList"
GRAIN_URL     = "http://apis.data.go.kr/1471000/MdcinGrnIdntfcInfoService03/getMdcinGrnIdntfcInfoList03"


def test_easy_drug():
    print("=" * 60)
    print("[1] e약은요 API 테스트")
    print("=" * 60)
    params = {
        "serviceKey": API_KEY,
        "type": "json",
        "numOfRows": 3,
        "pageNo": 1,
    }
    resp = requests.get(EASY_DRUG_URL, params=params, timeout=30)
    print(f"  Status: {resp.status_code}")
    data = resp.json()

    # 응답 구조 확인
    body = data.get("body", {})
    total_count = body.get("totalCount", "N/A")
    items = body.get("items", [])

    print(f"  총 데이터 수: {total_count}")
    print(f"  수신 건수: {len(items)}")

    if items:
        sample = items[0]
        print(f"\n  --- 샘플 항목 키 목록 ---")
        for k, v in sample.items():
            val_str = str(v)[:80] if v else "(없음)"
            print(f"    {k}: {val_str}")
    return total_count, items


def test_grain():
    print("\n" + "=" * 60)
    print("[2] 낱알식별 API 테스트")
    print("=" * 60)
    params = {
        "serviceKey": API_KEY,
        "type": "json",
        "numOfRows": 3,
        "pageNo": 1,
    }
    resp = requests.get(GRAIN_URL, params=params, timeout=30)
    print(f"  Status: {resp.status_code}")
    data = resp.json()

    body = data.get("body", {})
    total_count = body.get("totalCount", "N/A")
    items = body.get("items", [])

    print(f"  총 데이터 수: {total_count}")
    print(f"  수신 건수: {len(items)}")

    if items:
        sample = items[0]
        print(f"\n  --- 샘플 항목 키 목록 ---")
        for k, v in sample.items():
            val_str = str(v)[:80] if v else "(없음)"
            print(f"    {k}: {val_str}")
    return total_count, items


def test_join(easy_items, grain_items):
    """품목기준코드(itemSeq) 기준 JOIN 가능 여부 확인"""
    print("\n" + "=" * 60)
    print("[3] JOIN 키 확인")
    print("=" * 60)

    easy_keys = set(easy_items[0].keys()) if easy_items else set()
    grain_keys = set(grain_items[0].keys()) if grain_items else set()

    print(f"  e약은요 키: {sorted(easy_keys)}")
    print(f"  낱알식별 키: {sorted(grain_keys)}")
    print(f"  공통 키: {sorted(easy_keys & grain_keys)}")

    # itemSeq 값 샘플
    if easy_items:
        print(f"\n  e약은요 itemSeq 샘플: {easy_items[0].get('itemSeq', 'KEY없음')}")
    if grain_items:
        print(f"  낱알식별 itemSeq 샘플: {grain_items[0].get('itemSeq', 'KEY없음')}")


if __name__ == "__main__":
    try:
        total_easy, easy_items = test_easy_drug()
    except Exception as e:
        print(f"  [오류] {e}")
        easy_items = []
        total_easy = 0

    try:
        total_grain, grain_items = test_grain()
    except Exception as e:
        print(f"  [오류] {e}")
        grain_items = []

    if easy_items and grain_items:
        test_join(easy_items, grain_items)

    print("\n" + "=" * 60)
    print("[요약]")
    print(f"  e약은요 총 건수: {total_easy}")
    print(f"  낱알식별 총 건수: {total_grain if grain_items else 'N/A'}")
    print("=" * 60)
