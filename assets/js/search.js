// 이약뭐야? 검색 스크립트 (Fuse.js 기반)

const SEARCH_INDEX_URL = '/search_index.json';
const RECENT_KEY = 'iyak_recent';
const MAX_RECENT = 8;
const MAX_RESULTS = 60;

let fuse = null;
let allDrugs = [];
let activeType = 'drug'; // 'drug' | 'supplement'

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
    rebuildFuse();
    renderRecent();
    updateCategoryCounts();

    const params = new URLSearchParams(location.search);
    const q   = params.get('q');
    const tab = params.get('tab');
    const cat = params.get('cat');

    if (tab === 'supplement') switchTab('supplement');
    if (cat) {
      activeCat = cat;
      const btn = document.querySelector(`.cat-btn[data-cat="${cat}"]`);
      if (btn) { document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active')); btn.classList.add('active'); }
    }
    if (q) { document.getElementById('searchInput').value = q; doSearch(q, activeCat); }
    else if (cat) { doSearch('', cat); }
  } catch (e) {
    console.error('검색 인덱스 로드 실패', e);
  }
}

function rebuildFuse() {
  const filtered = allDrugs.filter(d => d.type === activeType);
  fuse = new Fuse(filtered, {
      keys: [
        { name: 'itemName',    weight: 0.5 },
        { name: 'efcyQesitm', weight: 0.3 },
        { name: 'entpName',   weight: 0.1 },
        { name: 'rawMaterial', weight: 0.1 },
      ],
      threshold: 0.35,
      includeScore: true,
      minMatchCharLength: 1,
    });
}

function updateCategoryCounts() {
  const drugs = allDrugs.filter(d => d.type === 'drug');
  Object.entries(CAT_KEYWORDS).forEach(([cat, kws]) => {
    const count = drugs.filter(d =>
      kws.some(kw => (d.efcyQesitm || '').includes(kw) || (d.itemName || '').includes(kw))
    ).length;
    const el = document.getElementById('cnt-' + cat);
    if (el) el.textContent = count.toLocaleString() + '개';
  });
}

function doSearch(query, cat = '') {
  if (!fuse) return;
  let results;
  if (!query && !cat) {
    renderGrid([]);
    return;
  }

  if (query) {
    results = fuse.search(query).map(r => r.item);
  } else {
    results = allDrugs.filter(d => d.type === activeType);
  }

  if (cat && CAT_KEYWORDS[cat]) {
    const kws = CAT_KEYWORDS[cat];
    results = results.filter(d =>
      kws.some(kw => (d.efcyQesitm || '').includes(kw) || (d.itemName || '').includes(kw))
    );
  }

  renderGrid(results.slice(0, MAX_RESULTS), query, results.length);
}

function setHomeSectionsVisible(visible) {
  const el = document.getElementById('homeSections');
  if (el) el.style.display = visible ? 'block' : 'none';
}

function renderGrid(items, query = '', total = 0) {
  const grid = document.getElementById('drugGrid');
  const header = document.getElementById('resultsHeader');
  const empty = document.getElementById('emptyState');
  const isSearching = query || activeCat;

  if (items.length === 0 && isSearching) {
    grid.innerHTML = '';
    header.style.display = 'none';
    empty.style.display = 'block';
    setHomeSectionsVisible(false);
    return;
  }
  empty.style.display = 'none';

  if (items.length > 0) {
    header.style.display = 'flex';
    document.getElementById('resultsCount').textContent = `총 ${total}건`;
    document.getElementById('resultsQuery').textContent = query ? `"${query}" 검색 결과` : '';
    setHomeSectionsVisible(false);
  } else {
    header.style.display = 'none';
    setHomeSectionsVisible(true);
  }

  grid.innerHTML = items.map(d => {
    const isSup = d.type === 'supplement';
    const href = isSup ? `/supplement/${d.slug}/` : `/drug/${d.slug}/`;
    const icon = isSup ? '🌿' : '💊';
    const img = d.itemImage
      ? `<img class="drug-card-image" src="${d.itemImage}" alt="${escHtml(d.itemName)}" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">`
      : '';
    const noImg = `<div class="drug-card-no-image" ${d.itemImage ? 'style="display:none"' : ''}>${icon}</div>`;
    const efcy = (d.efcyQesitm || '').slice(0, 60);
    const badge = isSup ? `<span class="tag tag-supplement" style="font-size:.72rem;padding:2px 8px">건강기능식품</span>` : '';
    return `<a class="drug-card" href="${href}" onclick="saveRecent('${d.slug}','${escHtml(d.itemName)}')">
      ${img}${noImg}
      <div class="drug-card-name">${escHtml(d.itemName)}</div>
      <div class="drug-card-company">${escHtml(d.entpName || '')}</div>
      ${efcy ? `<div class="drug-card-efcy">${escHtml(efcy)}</div>` : ''}
      ${badge}
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

// 탭 전환
function switchTab(type) {
  activeType = type;
  document.querySelectorAll('.main-tab').forEach(b => {
    b.classList.toggle('active', b.dataset.type === type);
  });
  const catFilter = document.getElementById('categoryFilter');
  if (catFilter) catFilter.style.display = type === 'drug' ? 'flex' : 'none';
  activeCat = '';
  document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
  const allBtn = document.querySelector('.cat-btn[data-cat=""]');
  if (allBtn) allBtn.classList.add('active');
  rebuildFuse();
  doSearch(document.getElementById('searchInput').value.trim());
}

document.querySelectorAll('.main-tab').forEach(btn => {
  btn.addEventListener('click', () => switchTab(btn.dataset.type));
});

// 카테고리 카드 클릭 (홈 섹션)
document.querySelectorAll('.category-card').forEach(card => {
  card.addEventListener('click', e => {
    e.preventDefault();
    const cat = card.dataset.cat;
    activeCat = cat;
    document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
    const btn = document.querySelector(`.cat-btn[data-cat="${cat}"]`);
    if (btn) btn.classList.add('active');
    window.scrollTo({ top: 0, behavior: 'smooth' });
    doSearch('', cat);
  });
});

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
