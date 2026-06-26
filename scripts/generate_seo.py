#!/usr/bin/env python3
"""
generate_seo.py - DeepSeek API로 약품별 SEO 설명문 생성

사용법:
  python scripts/generate_seo.py           # 전체 (seoDescription 없는 것만)
  python scripts/generate_seo.py --limit 50  # 50건만 테스트
  python scripts/generate_seo.py --force    # 기존 것도 덮어쓰기
"""
import json
import time
import argparse
from pathlib import Path
import requests

API_KEY_PATH = Path(r"C:\개인\개인 프로젝트\blogwriter_new\blogger_seo_bot\config\deepseek_api_key.txt")
DATA_FILE    = Path(__file__).parent.parent / "_data" / "drugs.json"
DELAY        = 0.15  # 요청 간격(초)

PROMPT_TMPL = """다음 의약품 정보를 바탕으로 네이버/구글 검색 최적화용 한국어 소개문을 120자 이내로 작성하세요.
효능과 주요 특징을 자연스럽게 담아주세요. 문장으로 끝내세요. 따옴표나 특수기호 없이.

제품명: {name}
업체명: {company}
효능: {efcy}
제형: {form}

소개문만 출력하세요 (설명 없이):"""


def get_api_key() -> str:
    return API_KEY_PATH.read_text(encoding="utf-8").strip()


def generate_desc(drug: dict, api_key: str) -> str:
    efcy = (drug.get("efcyQesitm") or "")[:150]
    prompt = PROMPT_TMPL.format(
        name=drug.get("itemName", ""),
        company=drug.get("entpName", ""),
        efcy=efcy,
        form=drug.get("formCodeName", ""),
    )
    resp = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200,
            "temperature": 0.5,
        },
        timeout=30,
    )
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"].strip()
    return text[:155]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    drugs = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    api_key = get_api_key()

    targets = [d for d in drugs if args.force or not d.get("seoDescription")]
    if args.limit:
        targets = targets[:args.limit]

    total = len(targets)
    print(f"생성 대상: {total}건\n")

    done = 0
    for drug in targets:
        try:
            desc = generate_desc(drug, api_key)
            drug["seoDescription"] = desc
            done += 1
            print(f"  [{done}/{total}] {drug['itemName'][:20]}: {desc[:50]}...")
        except Exception as e:
            print(f"  [실패] {drug.get('itemName', '')}: {e}")
        time.sleep(DELAY)

    # 저장 (전체 배열 업데이트)
    seq_map = {d["itemSeq"]: d for d in drugs}
    for t in targets:
        if t["itemSeq"] in seq_map:
            seq_map[t["itemSeq"]]["seoDescription"] = t.get("seoDescription", "")

    DATA_FILE.write_text(
        json.dumps(list(seq_map.values()), ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\n완료: {done}/{total}건 생성, {DATA_FILE} 저장")


if __name__ == "__main__":
    main()
