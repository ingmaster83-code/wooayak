#!/usr/bin/env python3
"""
식품안전나라 건강기능식품 API 테스트
URL 형식: http://openapi.foodsafetykorea.go.kr/api/{key}/{service}/json/{startIdx}/{endIdx}
"""
import json
import requests

API_KEY = "9fea81760dce4f86ac18"
BASE_URL = "http://openapi.foodsafetykorea.go.kr/api"

SERVICES = {
    "I0040": "건강기능식품 기능성 원료인정 현황",
    "I0041": "건강기능식품 영양DB",
    "I0042": "건강기능식품 개별인정형 정보",
    "I0044": "건강기능식품 품목분류정보",
}

def test_service(service_id, name):
    print(f"\n{'='*60}")
    print(f"[{service_id}] {name}")
    print('='*60)
    url = f"{BASE_URL}/{API_KEY}/{service_id}/json/1/3"
    try:
        resp = requests.get(url, timeout=15)
        print(f"  Status: {resp.status_code}")
        data = resp.json()

        # 응답 최상위 키 확인
        top_keys = list(data.keys())
        print(f"  최상위 키: {top_keys}")

        # 서비스 데이터 추출
        svc = data.get(service_id, {})
        total = svc.get("total_count", svc.get("TOTAL_COUNT", "N/A"))
        print(f"  총 건수: {total}")

        rows = svc.get("row", [])
        print(f"  수신 건수: {len(rows)}")

        if rows:
            sample = rows[0]
            print(f"\n  --- 샘플 항목 키 ---")
            for k, v in sample.items():
                val = str(v)[:70] if v else "(없음)"
                print(f"    {k}: {val}")
        return total, rows
    except Exception as e:
        print(f"  [오류] {e}")
        return 0, []

if __name__ == "__main__":
    for sid, name in SERVICES.items():
        total, rows = test_service(sid, name)
