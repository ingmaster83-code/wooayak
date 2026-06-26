// 알약 역검색 스크립트

const SEARCH_INDEX_URL = '/search_index.json';
let allDrugs = [];

async function loadIndex() {
  try {
    const resp = await fetch(SEARCH_INDEX_URL);
    allDrugs = await resp.json();
  } catch (e) {
    console.error('인덱스 로드 실패', e);
  }
}

// 선택 상태
const state = { form: '', shape: '', color: '', line: '' };

function bindToggle(groupId, stateKey) {
  document.getElementById(groupId).addEventListener('click', e => {
    const btn = e.target.closest('[data-val]');
    if (!btn) return;
    document.querySelectorAll(`#${groupId} [data-val]`).forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state[stateKey] = btn.dataset.val;
  });
}

bindToggle('formFilter',  'form');
bindToggle('shapeFilter', 'shape');
bindToggle('colorFilter', 'color');
bindToggle('lineFilter',  'line');

// 전체 버튼 기본 active
document.querySelectorAll('[data-val=""]').forEach(b => b.classList.add('active'));

document.getElementById('identifySearchBtn').addEventListener('click', doIdentify);

function doIdentify() {
  const print = document.getElementById('printInput').value.trim();
  const name  = document.getElementById('nameInput').value.trim().toLowerCase();

  let results = allDrugs.filter(d => {
    if (state.form  && !(d.formCodeName || '').includes(state.form))  return false;
    if (state.shape && (d.drugShape || '') !== state.shape)             return false;
    if (state.color && (d.colorClass1 || '') !== state.color &&
                       (d.colorClass2 || '') !== state.color)           return false;
    if (state.line  && (d.lineFront || '') !== state.line &&
                       (d.lineBack  || '') !== state.line)              return false;
    if (print && !(d.printFront || '').toLowerCase().includes(print.toLowerCase()) &&
                 !(d.printBack  || '').toLowerCase().includes(print.toLowerCase())) return false;
    if (name  && !(d.itemName   || '').toLowerCase().includes(name) &&
                 !(d.efcyQesitm || '').toLowerCase().includes(name))  return false;
    return true;
  });

  renderResults(results.slice(0, 60));
}

function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function renderResults(items) {
  const grid  = document.getElementById('identifyGrid');
  const empty = document.getElementById('identifyEmpty');

  if (!items.length) {
    grid.innerHTML = '';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';

  grid.innerHTML = items.map(d => {
    const img = d.itemImage
      ? `<img class="drug-card-image" src="${d.itemImage}" alt="${escHtml(d.itemName)}" loading="lazy">`
      : `<div class="drug-card-no-image">💊</div>`;
    return `<a class="drug-card" href="/drug/${d.slug}/">
      ${img}
      <div class="drug-card-name">${escHtml(d.itemName)}</div>
      <div class="drug-card-company">${escHtml(d.entpName || '')}</div>
      ${d.drugShape ? `<div class="drug-card-efcy">${escHtml(d.drugShape)} · ${escHtml(d.colorClass1 || '')}</div>` : ''}
    </a>`;
  }).join('');
}

loadIndex();
