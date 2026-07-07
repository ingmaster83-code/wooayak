#!/usr/bin/env python3
"""
generate_seo.py - DeepSeek API로 약품별 SEO 설명문 생성

사용법:
  python scripts/generate_seo.py           # 전체 (seoDescription 없는 것만)
  python scripts/generate_seo.py --limit 50  # 50건만 테스트
  python scripts/generate_seo.py --force    # 기존 것도 덮어쓰기
"""
import json
import sys
import time
import argparse
from pathlib import Path
import requests

sys.stdout.reconfigure(encoding='utf-8')

API_KEY_PATH = Path(r"C:\개인\개인 프로젝트\blogwriter_new\blogger_seo_bot\config\deepseek_api_key.txt")
DATA_FILE    = Path(__file__).parent.parent / "_rawdata" / "drugs.json"
DELAY        = 0.15

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

    seq_map = {d["itemSeq"]: i for i, d in enumerate(drugs)}

    done = 0
    for drug in targets:
        try:
            desc = generate_desc(drug, api_key)
            drug["seoDescription"] = desc
            idx = seq_map.get(drug["itemSeq"])
            if idx is not None:
                drugs[idx]["seoDescription"] = desc
            done += 1
            try:
                print(f"  [{done}/{total}] {drug['itemName'][:20]}: {desc[:40]}...")
            except Exception:
                print(f"  [{done}/{total}] (출력 생략)")
        except Exception as e:
            try:
                print(f"  [실패] {drug.get('itemName', '')}: {e}")
            except Exception:
                print(f"  [실패] (출력 불가): {e}")

        if done % 100 == 0:
            DATA_FILE.write_text(
                json.dumps(drugs, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            print(f"  [저장] {done}건 완료")

        time.sleep(DELAY)

    DATA_FILE.write_text(
        json.dumps(drugs, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\n완료: {done}/{total}건 생성")


if __name__ == "__main__":
    main()
