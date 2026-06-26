// 이약뭐야? 검색 스크립트 (Fuse.js 기반)

const SEARCH_INDEX_URL = '/search_index.json';
const RECENT_KEY = 'iyak_recent';
const MAX_RECENT = 8;
const MAX_RESULTS = 60;

let fuse = null;
let allDrugs = [];

// 카테고리 키워드 매핑
const CAT_KEYWORDS = {
  '해열진통': ['해열', '진통', '아세트아미노펜', '이부프로펜', '타이레놀', '애드빌'],
  '소화':     ['소화', '위장', '위염', '소화불량', '제산', '팽만'],
  '감기':     ['감기', '기침', '콧물', '인후', '비염', '코막힘'],
  '피부':     ['피부', '연고', '크림', '습진', '가려움', '두드러기', '항진균'],
  '비타민':   ['비타민', '미네랄', '영양', '철분', '칼슘', '마그네슘'],
  '눈':       ['안약', '눈', '결막', '충혈', '건조', '안구'],
  '소독':     ['소독', '상처', '포비돈', '과산화수소', '밴드'],
};

async function loadIndex() {
  try {
    const resp = await fetch(SEARCH_INDEX_URL);
    allDrugs = await resp.json();
    fuse = new Fuse(allDrugs, {
      keys: [
        { name: 'itemName',    weight: 0.5 },
        { name: 'efcyQesitm', weight: 0.3 },
        { name: 'entpName',   weight: 0.2 },
      ],
      threshold: 0.35,
      includeScore: true,
      minMatchCharLength: 1,
    });
    renderRecent();
    // URL 파라미터로 초기 검색
    const q = new URLSearchParams(location.search).get('q');
    if (q) {
      document.getElementById('searchInput').value = q;
      doSearch(q);
    }
  } catch (e) {
    console.error('검색 인덱스 로드 실패', e);
  }
}

function doSearch(query, cat = '') {
  if (!fuse) return;
  let results;
  if (!query && !cat) {
    renderGrid([]);
    return;
  }

  if (query) {
    // 초성 검색: ㄱ→가-깋 범위로 변환
    results = fuse.search(query).map(r => r.item);
  } else {
    results = [...allDrugs];
  }

  // 카테고리 필터
  if (cat && CAT_KEYWORDS[cat]) {
    const kws = CAT_KEYWORDS[cat];
    results = results.filter(d =>
      kws.some(kw => (d.efcyQesitm || '').includes(kw) || (d.itemName || '').includes(kw))
    );
  }

  renderGrid(results.slice(0, MAX_RESULTS), query, results.length);
}

function renderGrid(items, query = '', total = 0) {
  const grid = document.getElementById('drugGrid');
  const header = document.getElementById('resultsHeader');
  const empty = document.getElementById('emptyState');

  if (items.length === 0 && (query || activeCat)) {
    grid.innerHTML = '';
    header.style.display = 'none';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';

  if (items.length > 0) {
    header.style.display = 'flex';
    document.getElementById('resultsCount').textContent = `총 ${total}건`;
    document.getElementById('resultsQuery').textContent = query ? `"${query}" 검색 결과` : '';
  } else {
    header.style.display = 'none';
  }

  grid.innerHTML = items.map(d => {
    const img = d.itemImage
      ? `<img class="drug-card-image" src="${d.itemImage}" alt="${d.itemName}" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">`
      : '';
    const noImg = `<div class="drug-card-no-image" ${d.itemImage ? 'style="display:none"' : ''}>💊</div>`;
    const efcy = (d.efcyQesitm || '').slice(0, 60);
    return `<a class="drug-card" href="/drug/${d.slug}/" onclick="saveRecent('${d.slug}','${escHtml(d.itemName)}')">
      ${img}${noImg}
      <div class="drug-card-name">${escHtml(d.itemName)}</div>
      <div class="drug-card-company">${escHtml(d.entpName || '')}</div>
      ${efcy ? `<div class="drug-card-efcy">${escHtml(efcy)}</div>` : ''}
    </a>`;
  }).join('');
}

function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// 최근 조회
function saveRecent(slug, name) {
  let list = getRecent();
  list = list.filter(r => r.slug !== slug);
  list.unshift({ slug, name });
  if (list.length > MAX_RECENT) list = list.slice(0, MAX_RECENT);
  localStorage.setItem(RECENT_KEY, JSON.stringify(list));
}

function getRecent() {
  try { return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'); } catch { return []; }
}

function renderRecent() {
  const list = getRecent();
  const sec = document.getElementById('recentSection');
  const cont = document.getElementById('recentList');
  if (!list.length) { sec.style.display = 'none'; return; }
  sec.style.display = 'block';
  cont.innerHTML = list.map(r =>
    `<a class="recent-item" href="/drug/${r.slug}/">${escHtml(r.name)}</a>`
  ).join('');
}

// 이벤트
let activeCat = '';
let searchTimer = null;

document.getElementById('searchInput').addEventListener('input', e => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => doSearch(e.target.value.trim(), activeCat), 200);
});

document.getElementById('searchBtn').addEventListener('click', () => {
  doSearch(document.getElementById('searchInput').value.trim(), activeCat);
});

document.getElementById('searchInput').addEventListener('keydown', e => {
  if (e.key === 'Enter') doSearch(e.target.value.trim(), activeCat);
});

document.getElementById('categoryFilter').addEventListener('click', e => {
  const btn = e.target.closest('.cat-btn');
  if (!btn) return;
  document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  activeCat = btn.dataset.cat;
  doSearch(document.getElementById('searchInput').value.trim(), activeCat);
});

loadIndex();
