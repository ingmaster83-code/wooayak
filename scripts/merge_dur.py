#!/usr/bin/env python3
"""
merge_dur.py - dur_taboo.json을 drugs.json에 병합 (durTaboo 필드 추가)

fetch_drugs.py를 재실행하면 drugs.json이 API에서 통째로 새로 생성되므로,
DUR 데이터를 유지하려면 이 스크립트를 fetch_drugs.py 다음에 항상 실행해야 한다.
순서: fetch_drugs.py -> fetch_dur_taboo.py -> merge_dur.py (마지막) -> generate_seo.py
"""
import json
from pathlib import Path

DRUGS_PATH = Path(__file__).parent.parent / "_rawdata" / "drugs.json"
DUR_PATH = Path(__file__).parent.parent / "_rawdata" / "dur_taboo.json"


def main():
    if not DUR_PATH.exists():
        print(f"[스킵] {DUR_PATH} 없음 — fetch_dur_taboo.py 먼저 실행하세요")
        return

    drugs = json.loads(DRUGS_PATH.read_text(encoding="utf-8"))
    dur = json.loads(DUR_PATH.read_text(encoding="utf-8"))

    matched = 0
    for d in drugs:
        taboos = dur.get(d.get("itemSeq", ""), [])
        d["durTaboo"] = taboos
        if taboos:
            matched += 1

    DRUGS_PATH.write_text(
        json.dumps(drugs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"완료: {len(drugs)}개 약품 중 {matched}개에 병용금기 정보 병합됨")


if __name__ == "__main__":
    main()
