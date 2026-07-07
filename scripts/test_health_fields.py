import requests, json, sys
sys.stdout.reconfigure(encoding='utf-8')

key = '9fea81760dce4f86ac18'
services = ['I2710', 'I-0040', 'I-0050', 'I0760']

for sid in services:
    url = f'http://openapi.foodsafetykorea.go.kr/api/{key}/{sid}/json/1/2'
    try:
        r = requests.get(url, timeout=30)
        data = r.json()
        svc = data.get(sid, {})
        total = svc.get('total_count', '?')
        rows = svc.get('row', [])
        print(f'=== [{sid}] 총 {total}건 ===')
        if rows:
            for k, v in rows[0].items():
                print(f'  {k}: {str(v)[:70]}')
        print()
    except Exception as e:
        print(f'[{sid}] 오류: {e}')
        print()
