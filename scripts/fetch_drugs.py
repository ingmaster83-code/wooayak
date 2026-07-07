#!/usr/bin/env python3
"""
fetch_drugs.py - ?ì•½ì²?API ?„ì²´ ?°ì´???˜ì§‘ ??_rawdata/drugs.json ?ì„±

?˜ì§‘ ?€??
  1. e?½ì???API (DrbEasyDrugInfoService) - ?¨ëŠ¥/?©ë²•/ì£¼ì˜?¬í•­ ??  2. ?±ì•Œ?ë³„ API (MdcinGrnIdntfcInfoService03) - ëª¨ì–‘/?‰ìƒ/?´ë?ì§€ ??
JOIN ?? itemSeq (e?½ì??? == ITEM_SEQ (?±ì•Œ?ë³„)

?¬ìš©ë²?
  python scripts/fetch_drugs.py
  python scripts/fetch_drugs.py --limit 100   # ?ŒìŠ¤?¸ìš© 100ê±´ë§Œ
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

BATCH = 100   # 1???”ì²­??ê±´ìˆ˜ (API ìµœë? 100)
DELAY = 0.3   # ?”ì²­ ê°„ê²©(ì´?


def fetch_all(url: str, extra_params: dict = None, limit: int = 0) -> list:
    """?˜ì´ì§€?¤ì´?˜ìœ¼ë¡??„ì²´ ?°ì´???˜ì§‘"""
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
                print(f"  [?¬ì‹œ??{retry}/5] page={page}: {e} ??{wait:.0f}ì´??€ê¸?)
                time.sleep(wait)
        else:
            print(f"  [?¬ê¸°] page={page} 5???¤íŒ¨, ?¤ìŒ?¼ë¡œ ì§„í–‰")
            break

        body = data.get("body", {})
        page_items = body.get("items", [])

        if not page_items:
            break

        # ë¦¬ìŠ¤?¸ê? ?„ë‹Œ ê²½ìš°(?¨ì¼ dict) ì²˜ë¦¬
        if isinstance(page_items, dict):
            page_items = [page_items]

        items.extend(page_items)

        total = int(body.get("totalCount", 0))
        print(f"  page {page:3d} | ?˜ì§‘ {len(items):5d} / {total}")

        if limit and len(items) >= limit:
            items = items[:limit]
            break

        if len(items) >= total:
            break

        page += 1
        time.sleep(DELAY)

    return items


def clean_text(text) -> str:
    """ë¶ˆí•„?”í•œ ê³µë°±Â·?œê·¸ ?œê±°"""
    if not text or str(text).strip() in ("(?†ìŒ)", "?†ìŒ", ""):
        return ""
    text = str(text)
    # ê°„ë‹¨??HTML ?œê·¸ ?œê±°
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("\xa0", " ").strip()
    return text


def slugify(name: str) -> str:
    """?œí’ˆëª…ì„ URL-safe slugë¡?ë³€??""
    # ?œê?Â·?ìˆ«?Â·í•˜?´í”ˆë§??ˆìš©
    name = re.sub(r"[^\w\sê°€-??", "", name)
    name = re.sub(r"\s+", "-", name.strip())
    return name[:60].strip("-").lower()


def build_drug_record(easy: dict, grain: dict = None) -> dict:
    """e?½ì???+ ?±ì•Œ?ë³„ ?°ì´?°ë? ?˜ë‚˜???ˆì½”?œë¡œ ?©ì¹˜ê¸?""
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
        # ?±ì•Œ?ë³„ (?†ìœ¼ë©?ë¹ˆê°’)
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
        # SEO??(generate_seo.py?ì„œ ì±„ì?)
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
            # ?±ì•Œ ?´ë?ì§€ê°€ ?ˆìœ¼ë©??°ì„  ?¬ìš©
            "itemImage":    clean_text(grain.get("ITEM_IMAGE", "")) or record["itemImage"],
        })

    return record


def main():
    parser = argparse.ArgumentParser(description="?ì•½ì²?API ?„ì²´ ?˜ì§‘")
    parser.add_argument("--limit", type=int, default=0, help="?ŒìŠ¤?¸ìš© ê±´ìˆ˜ ?œí•œ (0=?„ì²´)")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ?€?€ Step 1: e?½ì????„ì²´ ?˜ì§‘ ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
    print("\n[Step 1] e?½ì???API ?˜ì§‘ ì¤?..")
    easy_items = fetch_all(EASY_DRUG_URL, limit=args.limit)
    print(f"  ??ì´?{len(easy_items)}ê±??˜ì§‘ ?„ë£Œ\n")

    # itemSeq ??easy dict ?¸ë±??    easy_index = {str(item.get("itemSeq", "")): item for item in easy_items}

    # ?€?€ Step 2: ?±ì•Œ?ë³„ ?„ì²´ ?˜ì§‘ ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
    print("[Step 2] ?±ì•Œ?ë³„ API ?˜ì§‘ ì¤?..")
    grain_items = fetch_all(GRAIN_URL, limit=0)  # ?±ì•Œ?€ ??ƒ ?„ì²´
    print(f"  ??ì´?{len(grain_items)}ê±??˜ì§‘ ?„ë£Œ\n")

    # ITEM_SEQ ??grain dict ?¸ë±??    grain_index = {str(item.get("ITEM_SEQ", "")): item for item in grain_items}

    # ?€?€ Step 3: JOIN ë°??ˆì½”???ì„± ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
    print("[Step 3] ?°ì´??ë³‘í•© ì¤?..")
    drugs = []
    matched = 0
    for seq, easy in easy_index.items():
        grain = grain_index.get(seq)
        if grain:
            matched += 1
        record = build_drug_record(easy, grain)
        drugs.append(record)

    print(f"  ???±ì•Œ?ë³„ ë§¤ì¹­: {matched} / {len(drugs)}ê±?)

    # ?€?€ Step 4: ?€???€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
    OUT_FILE.write_text(
        json.dumps(drugs, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\n[?„ë£Œ] {OUT_FILE}")
    print(f"  ì´?{len(drugs)}ê°??½í’ˆ ?€??)
    print(f"  ?Œì¼ ?¬ê¸°: {OUT_FILE.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
