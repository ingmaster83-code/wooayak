/* 약 가격 검색: /price/search.json = ["p",제품명,제조사,가격,slug,단위] | ["g",성분명,약수,slug] */
(function () {
  var q = document.getElementById('pq'), box = document.getElementById('psr');
  if (!q || !box) return;
  var data = null, loading = false;
  function load(cb) {
    if (data) return cb();
    if (loading) return;
    loading = true;
    fetch('/price/search.json').then(function (r) { return r.json(); }).then(function (j) { data = j; cb(); }).catch(function () { loading = false; });
  }
  function norm(s) { return s.replace(/\s/g, '').toLowerCase(); }
  function render() {
    var t = norm(q.value);
    if (!t || !data) { box.style.display = 'none'; return; }
    var g = [], a = [], b = [];
    for (var i = 0; i < data.length; i++) {
      var d = data[i], p = norm(d[1]).indexOf(t);
      if (p < 0) continue;
      if (d[0] === 'g') { if (g.length < 5) g.push(d); }
      else if (p === 0) { if (a.length < 12) a.push(d); } else if (b.length < 12) b.push(d);
      if (g.length >= 5 && a.length >= 12) break;
    }
    var res = g.concat(a, b).slice(0, 14);
    if (!res.length) { box.innerHTML = '<a href="#" onclick="return false">검색 결과가 없습니다 (건강보험 급여 약만 수록)</a>'; box.style.display = 'block'; return; }
    box.innerHTML = res.map(function (d) {
      if (d[0] === 'g') return '<a href="/price/ingredient/' + encodeURI(d[3]) + '/">🧪 ' + d[1] + '<small>성분 · 급여 약 ' + d[2] + '개 비교</small></a>';
      return '<a href="/price/drug/' + encodeURI(d[4]) + '/">' + d[1] + '<small>' + d[2] + ' · ' + Number(d[3]).toLocaleString('ko-KR') + '원/' + d[5] + '</small></a>';
    }).join('');
    box.style.display = 'block';
  }
  q.addEventListener('focus', function () { load(render); });
  q.addEventListener('input', function () { load(render); });
  document.addEventListener('click', function (e) { if (!box.contains(e.target) && e.target !== q) box.style.display = 'none'; });
})();
