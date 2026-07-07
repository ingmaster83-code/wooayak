#!/usr/bin/env python3
"""
fetch_health.py - ?ùÌíà?àÏ†Ñ?òÎùº Í±¥Í∞ïÍ∏∞Îä•?ùÌíà API ?ÑÏ≤¥ ?òÏßë
Í≤∞Í≥ºÎ•?_rawdata/supplements.json?ºÎ°ú ?Ä??
?¨Ïö©Î≤?
  python scripts/fetch_health.py
  python scripts/fetch_health.py --limit 50  # ?åÏä§??"""
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
                print(f"  [?¨Ïãú??{retry}/5] {service_id} start={start}: {e} ??{wait:.0f}Ï¥??ÄÍ∏?)
                time.sleep(wait)

        if data is None:
            print(f"  [?¨Í∏∞] {service_id} start={start}")
            break

        svc   = data.get(service_id, {})
        total = int(svc.get("total_count", 0))
        rows  = svc.get("row", [])

        if not rows:
            break
        if isinstance(rows, dict):
            rows = [rows]

        items.extend(rows)
        print(f"  {service_id} | {start}~{end} | ?òÏßë {len(items):5d} / {total}")

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
    if text in ("(?ÜÏùå)", "?ÜÏùå", "-", ""):
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    return text.replace("\xa0", " ").strip()


def slugify(name: str) -> str:
    name = re.sub(r"[^\w\sÍ∞Ä-??", "", name)
    name = re.sub(r"\s+", "-", name.strip())
    return name[:60].strip("-").lower()


def build_supplement(row: dict, source: str) -> dict:
    """I2710(?àÎ™©Î∂ÑÎ•ò) Í∏∞Î∞ò ?àÏΩî???ùÏÑ±"""
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
    """I-0040(Í∏∞Îä•???êÎ£å?∏Ï†ï) Í∏∞Î∞ò ?àÏΩî??""
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
    """I-0050(Í∞úÎ≥Ñ?∏Ï†ï?? Í∏∞Î∞ò ?àÏΩî??""
    name = clean(row.get("RAWMTRL_NM", ""))
    if not name:
        return None

    uid = f"sup-{slugify(name)}"
    fnclty = clean(row.get("PRIMARY_FNCLTY", ""))
    # Íµ?¨∏Îß?Ï∂îÏ∂ú
    ko_match = re.search(r"[Ôº?(]Íµ?¨∏[Ôº?)](.*?)(?:[Ôº?(]?ÅÎ¨∏[Ôº?)]|$)", fnclty, re.DOTALL)
    if ko_match:
        fnclty = ko_match.group(1).strip()

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
    supplements = {}  # slug ??record (Ï§ëÎ≥µ ?úÍ±∞)

    # ?Ä?Ä Step 1: I2710 ?àÎ™©Î∂ÑÎ•ò (Î©îÏù∏) ?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä
    print("\n[Step 1] I2710 ?àÎ™©Î∂ÑÎ•ò?ïÎ≥¥ ?òÏßë...")
    rows = fetch_all("I2710", args.limit)
    for row in rows:
        rec = build_supplement(row, "I2710")
        if rec and rec["slug"] not in supplements:
            supplements[rec["slug"]] = rec
    print(f"  ??{len(supplements)}Í±??±Î°ù\n")

    # ?Ä?Ä Step 2: I-0040 Í∏∞Îä•???êÎ£å?∏Ï†ï ?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä
    print("[Step 2] I-0040 Í∏∞Îä•???êÎ£å?∏Ï†ï?ÑÌô© ?òÏßë...")
    rows = fetch_all("I-0040", args.limit)
    added = 0
    for row in rows:
        rec = build_from_i0040(row)
        if rec and rec["slug"] not in supplements:
            supplements[rec["slug"]] = rec
            added += 1
        elif rec and rec["slug"] in supplements:
            # Í∏∞Ï°¥ ?àÏΩî?úÏóê Í∏∞Îä•??Î≥¥ÏôÑ
            existing = supplements[rec["slug"]]
            if not existing["primaryFnclty"] and rec["primaryFnclty"]:
                existing["primaryFnclty"] = rec["primaryFnclty"]
            if not existing["caution"] and rec["caution"]:
                existing["caution"] = rec["caution"]
    print(f"  ??{added}Í±??†Í∑ú Ï∂îÍ?, Ï¥?{len(supplements)}Í±?n")

    # ?Ä?Ä Step 3: I-0050 Í∞úÎ≥Ñ?∏Ï†ï???Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä
    print("[Step 3] I-0050 Í∞úÎ≥Ñ?∏Ï†ï???ïÎ≥¥ ?òÏßë...")
    rows = fetch_all("I-0050", args.limit)
    added = 0
    for row in rows:
        rec = build_from_i0050(row)
        if rec and rec["slug"] not in supplements:
            supplements[rec["slug"]] = rec
            added += 1
    print(f"  ??{added}Í±??†Í∑ú Ï∂îÍ?, Ï¥?{len(supplements)}Í±?n")

    # ?Ä?Ä Step 4: ?Ä???Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä?Ä
    result = list(supplements.values())
    # Í∏∞Îä•???ïÎ≥¥ ?ÜÎäî ??™© ?úÍ±∞
    result = [r for r in result if r["primaryFnclty"] or r["rawMaterial"]]

    OUT_FILE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"[?ÑÎ£å] {OUT_FILE}")
    print(f"  Ï¥?{len(result)}Í∞?Í±¥Í∞ïÍ∏∞Îä•?ùÌíà ?Ä??)
    print(f"  ?åÏùº ?¨Í∏∞: {OUT_FILE.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
