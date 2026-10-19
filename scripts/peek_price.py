# -*- coding: utf-8 -*-
import sys, re, pathlib
sys.stdout.reconfigure(encoding="utf-8")
root = pathlib.Path(__file__).resolve().parent.parent
p = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 2500
t = (root / p.strip("/") / "index.html").read_text(encoding="utf-8")
print("TITLE:", re.search(r"<title>(.*?)</title>", t).group(1)); print("DESC:", re.search(r'name="description" content="(.*?)"', t).group(1))
b = re.search(r'<div class="price-page">(.*?)</div></main>', t, re.S).group(1)
b = re.sub(r"<script.*?</script>", "", b, flags=re.S); b = re.sub(r"</(tr|p|h1|h2|div|li)>", "\n", b); b = re.sub(r"</t[dh]>", " | ", b); b = re.sub(r"<[^>]+>", "", b); b = re.sub(r"\n\s*\n+", "\n", b)
print(b[:n])
