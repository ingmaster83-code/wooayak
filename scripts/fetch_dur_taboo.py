#!/usr/bin/env python3
"""
fetch_dur_taboo.py - DUR(의약품안전사용서비스) 병용금기 정보 수집

drugs.json에 있는 각 약품(itemSeq)에 대해 식약처 DUR API로
"이 약과 같이 먹으면 안 되는 약" 목록을 조회해서 _rawdata/dur_taboo.json으로 저장한다.
전체 79만 건을 통째로 받는 대신, itemSeq 필터로 약품별 개별 조회(병렬)하는 방식.

사용법:
  python scripts/fetch_dur_taboo.py
  python scripts/fetch_dur_taboo.py --limit 100   # 테스트용 100개 약품만
"""
import argparse
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

API_KEY = "9490b1d34e92aa9e25b32a4cff1438fc7b9c71e5d332413916a391e867f61e86"
BASE_URL = "https://apis.data.go.kr/1471000/DURPrdlstInfoService03/getUsjntTabooInfoList03"

DRUGS_PATH = Path(__file__).parent.parent / "_rawdata" / "drugs.json"
OUT_PATH = Path(__file__).parent.parent / "_rawdata" / "dur_taboo.json"


def fetch_page(item_seq, page_no, num_of_rows=100):
    params = {
        "serviceKey": API_KEY, "type": "json",
        "numOfRows": num_of_rows, "pageNo": page_no,
        "itemSeq": item_seq,
    }
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            body = data.get("body", {})
            total = int(body.get("totalCount", 0))
            items = body.get("items", [])
            if isinstance(items, dict):
                items = [items]
            return items, total
        except Exception as e:
            time.sleep(1.0 * (attempt + 1))
    return [], 0


def fetch_one(item_seq):
    items, total = fetch_page(item_seq, 1, 100)
    if total > 100:
        page = 2
        while len(items) < total:
            more, _ = fetch_page(item_seq, page, 100)
            if not more:
                break
            items.extend(more)
            page += 1
            time.sleep(0.1)

    taboos = []
    seen = set()
    for it in items:
        mix_seq = it.get("MIXTURE_ITEM_SEQ", "")
        key = (mix_seq, it.get("TYPE_NAME", ""))
        if key in seen:
            continue
        seen.add(key)
        taboos.append({
            "typeName": it.get("TYPE_NAME", ""),
            "ingrName": it.get("INGR_KOR_NAME", ""),
            "mixtureItemSeq": mix_seq,
            "mixtureItemName": it.get("MIXTURE_ITEM_NAME", ""),
            "mixtureEntpName": it.get("MIXTURE_ENTP_NAME", ""),
            "mixtureIngrName": it.get("MIXTURE_INGR_KOR_NAME", ""),
            "prohbtContent": it.get("PROHBT_CONTENT", "") or "",
        })
    return item_seq, taboos


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    drugs = json.loads(DRUGS_PATH.read_text(encoding="utf-8"))
    item_seqs = [d["itemSeq"] for d in drugs if d.get("itemSeq")]
    if args.limit:
        item_seqs = item_seqs[: args.limit]
    print(f"대상 약품 수: {len(item_seqs)}")

    result = {}
    done = 0
    with_taboo = 0
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(fetch_one, seq): seq for seq in item_seqs}
        for fut in as_completed(futures):
            seq, taboos = fut.result()
            if taboos:
                result[seq] = taboos
                with_taboo += 1
            done += 1
            if done % 200 == 0:
                print(f"  진행 {done}/{len(item_seqs)} (병용금기 있음: {with_taboo}건)")

    OUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n완료: {len(item_seqs)}개 약품 중 {with_taboo}개에 병용금기 정보 있음")
    print(f"저장: {OUT_PATH}")


if __name__ == "__main__":
    main()
