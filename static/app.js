/* ─────────────────────────────────────────────────
   RECON — Frontend Logic
   • Form submission + progress simulation
   • Data rendering (identity, sentiment, red flags, timeline, themes, word cloud, reviews)
   • Chart.js integration
   • Canvas-based word cloud
   • Review filtering
   • JSON/CSV export
───────────────────────────────────────────────── */

'use strict';

// ── State ──────────────────────────────────────────────
let scraped_data = null;
let all_reviews  = [];
let sentimentChart = null;
let timelineChart  = null;

// ── Avatar colors ──────────────────────────────────────
const AVATAR_COLORS = [
  '#6366f1','#a855f7','#ec4899','#ef4444','#f97316',
  '#eab308','#22c55e','#14b8a6','#0ea5e9','#3b82f6'
];

// ── DOM helpers ────────────────────────────────────────
const $  = id => document.getElementById(id);
const el = (tag, cls) => { const e = document.createElement(tag); if (cls) e.className = cls; return e; };

// ── FORM SUBMIT ─────────────────────────────────────────
document.getElementById('search-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const company  = $('company-input').value.trim();
  const location = $('location-input').value.trim();
  if (!company || !location) return;

  startProgress();
  hideResults();
  hideToast();

  try {
    const response = await fetch('/scrape', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ company, location })
    });
    const data = await response.json();

    if (!response.ok || data.error) {
      showError(data.error || 'Scraping failed. The business may not be found on Google Maps.');
      stopProgress();
      return;
    }

    scraped_data = data;
    all_reviews  = data.reviews || [];

    await completeProgress();
    renderAll(data);

  } catch (err) {
    showError('Network error: ' + err.message);
    stopProgress();
  }
});

// ── PROGRESS ANIMATION ──────────────────────────────────
let progressInterval = null;
let progressStep = 0;

function startProgress() {
  $('scrape-btn').disabled = true;
  $('progress-area').classList.remove('hidden');
  $('results-container').classList.add('hidden');

  progressStep = 0;
  const bar   = $('progress-bar');
  const steps = document.querySelectorAll('.step');

  steps.forEach((s, i) => {
    s.classList.remove('active', 'done');
    if (i === 0) s.classList.add('active');
  });
  bar.style.width = '0%';

  let pct = 0;
  progressInterval = setInterval(() => {
    if (pct < 85) {
      pct += Math.random() * 1.5;
      bar.style.width = Math.min(pct, 85) + '%';

      // Advance steps
      if (pct > 20 && progressStep === 0) { progressStep = 1; activateStep(steps, 1); }
      if (pct > 50 && progressStep === 1) { progressStep = 2; activateStep(steps, 2); }
      if (pct > 75 && progressStep === 2) { progressStep = 3; activateStep(steps, 3); }
    }
  }, 300);
}

function activateStep(steps, idx) {
  steps.forEach((s, i) => {
    if (i < idx) { s.classList.remove('active'); s.classList.add('done'); }
    else if (i === idx) { s.classList.add('active'); }
    else { s.classList.remove('active', 'done'); }
  });
}

async function completeProgress() {
  clearInterval(progressInterval);
  const bar = $('progress-bar');
  bar.style.width = '100%';
  const steps = document.querySelectorAll('.step');
  steps.forEach(s => { s.classList.remove('active'); s.classList.add('done'); });
  await sleep(600);
  $('progress-area').classList.add('hidden');
  $('scrape-btn').disabled = false;
}

function stopProgress() {
  clearInterval(progressInterval);
  $('progress-area').classList.add('hidden');
  $('scrape-btn').disabled = false;
}

function hideResults() { $('results-container').classList.add('hidden'); }
function sleep(ms)     { return new Promise(r => setTimeout(r, ms)); }

// ── RENDER ALL ──────────────────────────────────────────
function renderAll(data) {
  renderIdentity(data);
  renderSentiment(data);
  renderRedFlags(data.red_flags || []);
  renderTimeline(data.timeline || []);
  renderThemes(data.themes || {});
  renderWordCloud(data.word_freq || []);
  renderHours(data.hours || []);
  renderReviews(all_reviews);

  $('results-container').classList.remove('hidden');
  $('results-container').scrollIntoView({ behavior: 'smooth' });
}

// ── IDENTITY ────────────────────────────────────────────
function renderIdentity(data) {
  const name = data.name || data.company || '—';
  $('biz-name').textContent = name;
  $('biz-category').textContent = data.category || '';
  $('biz-address').textContent  = '📍 ' + (data.address || 'N/A');
  $('biz-phone').textContent    = '📞 ' + (data.phone   || 'N/A');
  $('biz-website').textContent  = '🌐 ' + (data.website || 'N/A');

  // Avatar initials
  const initials = name.split(' ').slice(0,2).map(w => w[0]?.toUpperCase() || '').join('');
  const color    = AVATAR_COLORS[name.charCodeAt(0) % AVATAR_COLORS.length];
  const avatar   = $('biz-avatar');
  avatar.textContent = initials || '🏢';
  avatar.style.background = `linear-gradient(135deg, ${color}, ${shiftHue(color, 40)})`;

  // Rating
  const rating = data.rating;
  if (rating) {
    $('rating-num').textContent = rating.toFixed(1);
    $('stars-display').textContent = renderStars(rating);
  } else {
    $('rating-num').textContent = '—';
  }
  $('review-count-text').textContent = data.review_count
    ? data.review_count.toLocaleString() + ' reviews scraped'
    : (all_reviews.length > 0 ? all_reviews.length + ' reviews found' : 'No review count');
}

function renderStars(rating) {
  let s = '';
  for (let i = 1; i <= 5; i++) {
    if (rating >= i)      s += '⭐';
    else if (rating > i-1) s += '✨';
    else                   s += '☆';
  }
  return s;
}

function shiftHue(hex, amount) {
  // Approximation: just return a purple-ish variant
  return '#a855f7';
}

// ── SENTIMENT ───────────────────────────────────────────
function renderSentiment(data) {
  const ss = data.sentiment_summary || {};
  const labels = ss.labels || { positive: 0, negative: 0, mixed: 0, neutral: 0 };
  const total  = labels.positive + labels.negative + labels.mixed + labels.neutral || 1;

  const posPct = Math.round(labels.positive / total * 100);
  $('donut-pct').textContent = posPct + '%';

  // Animated bars
  setTimeout(() => {
    setBar('bar-pos', labels.positive, total);
    setBar('bar-neg', labels.negative, total);
    setBar('bar-mix', labels.mixed,    total);
    setBar('bar-neu', labels.neutral,  total);
  }, 300);

  $('cnt-pos').textContent = labels.positive;
  $('cnt-neg').textContent = labels.negative;
  $('cnt-mix').textContent = labels.mixed;
  $('cnt-neu').textContent = labels.neutral;

  // Donut chart
  if (sentimentChart) sentimentChart.destroy();
  const ctx = document.getElementById('sentiment-chart').getContext('2d');
  sentimentChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Positive', 'Negative', 'Mixed', 'Neutral'],
      datasets: [{
        data: [labels.positive, labels.negative, labels.mixed, labels.neutral],
        backgroundColor: ['#22d3a7', '#f87171', '#fbbf24', '#475569'],
        borderColor: 'transparent',
        borderWidth: 0,
        hoverOffset: 6
      }]
    },
    options: {
      cutout: '72%',
      plugins: { legend: { display: false }, tooltip: {
        callbacks: {
          label: ctx => ` ${ctx.label}: ${ctx.raw} reviews`
        }
      }},
      animation: { duration: 1000, easing: 'easeInOutQuart' }
    }
  });
}

function setBar(id, val, total) {
  const pct = Math.round(val / total * 100);
  $(id).style.width = pct + '%';
}

// ── RED FLAGS ───────────────────────────────────────────
function renderRedFlags(flags) {
  const body = $('red-flags-body');
  if (!flags.length) {
    body.innerHTML = '<p class="empty-msg">✅ No significant red flags detected in reviews.</p>';
    return;
  }
  const maxCount = flags[0].count;
  body.innerHTML = '';
  flags.forEach((f, i) => {
    const pct = Math.round(f.count / maxCount * 100);
    const div = el('div', 'red-flag-item');
    div.innerHTML = `
      <span class="flag-word">⚠ ${f.word}</span>
      <div class="flag-meter-track">
        <div class="flag-meter-fill" id="flag-${i}" style="width:0%"></div>
      </div>
      <span class="flag-count">${f.count}×</span>
    `;
    body.appendChild(div);
    setTimeout(() => { document.getElementById(`flag-${i}`).style.width = pct + '%'; }, 200 + i * 80);
  });
}

// ── TIMELINE CHART ──────────────────────────────────────
function renderTimeline(timeline) {
  if (timelineChart) timelineChart.destroy();
  const ctx = document.getElementById('timeline-chart').getContext('2d');

  if (!timeline.length) {
    ctx.fillStyle = 'rgba(255,255,255,0.1)';
    ctx.font = '14px Inter';
    ctx.fillText('Not enough review dates to build timeline.', 20, 110);
    return;
  }

  const labels = timeline.map(t => t.month);
  const values = timeline.map(t => t.avg_rating);
  const counts = timeline.map(t => t.count);

  timelineChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Avg Rating',
        data: values,
        borderColor: '#00e5ff',
        backgroundColor: 'rgba(0,229,255,0.08)',
        borderWidth: 2.5,
        pointBackgroundColor: '#00e5ff',
        pointRadius: 5,
        pointHoverRadius: 8,
        tension: 0.4,
        fill: true
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        y: {
          min: 1, max: 5,
          ticks: { color: '#475569', stepSize: 1 },
          grid: { color: 'rgba(255,255,255,0.05)' }
        },
        x: {
          ticks: { color: '#475569', maxRotation: 30 },
          grid: { color: 'rgba(255,255,255,0.04)' }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: ctx => ctx[0].label,
            label: ctx => ` ${ctx.parsed.y.toFixed(2)} ★  (${counts[ctx.dataIndex]} reviews)`
          },
          backgroundColor: 'rgba(8,13,26,0.9)',
          borderColor: 'rgba(255,255,255,0.1)',
          borderWidth: 1
        }
      },
      animation: { duration: 1200 }
    }
  });
}

// ── THEMES ──────────────────────────────────────────────
function renderThemes(themes) {
  const body = $('themes-body');
  body.innerHTML = '';
  const entries = Object.entries(themes).sort((a, b) => b[1].mentions - a[1].mentions);
  if (!entries.length || entries.every(([,v]) => v.mentions === 0)) {
    body.innerHTML = '<p class="empty-msg" style="color:#475569;font-size:.85rem">No themes extracted yet.</p>';
    return;
  }
  const maxMentions = Math.max(...entries.map(([,v]) => v.mentions)) || 1;
  entries.forEach(([theme, data], idx) => {
    if (data.mentions === 0) return;
    const posW = Math.round(data.positive / data.mentions * 100);
    const negW = Math.round(data.negative / data.mentions * 100);
    const div = el('div', 'theme-item');
    div.innerHTML = `
      <div class="theme-header">
        <span class="theme-name">${theme}</span>
        <span class="theme-count">${data.mentions} mentions</span>
      </div>
      <div class="theme-bar-track">
        <div class="theme-bar-pos" id="tpos-${idx}" style="width:0%"></div>
        <div class="theme-bar-neg" id="tneg-${idx}" style="width:0%"></div>
      </div>
    `;
    body.appendChild(div);
    setTimeout(() => {
      document.getElementById(`tpos-${idx}`).style.width = posW + '%';
      document.getElementById(`tneg-${idx}`).style.width = negW + '%';
    }, 300 + idx * 60);
  });
}

// ── WORD CLOUD (canvas-based) ───────────────────────────
function renderWordCloud(words) {
  const canvas = document.getElementById('word-cloud-canvas');
  const ctx    = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);

  if (!words || !words.length) {
    ctx.fillStyle = '#475569';
    ctx.font = '14px Inter';
    ctx.fillText('No review text to generate word cloud.', 20, H / 2);
    return;
  }

  const maxCount = words[0].count;
  const palette  = ['#00e5ff','#a855f7','#ec4899','#22d3a7','#fbbf24','#f97316','#6366f1','#14b8a6'];
  const placed   = [];

  function overlaps(x, y, w, h) {
    return placed.some(p =>
      x < p.x + p.w + 10 &&
      x + w + 10 > p.x   &&
      y < p.y + p.h + 10 &&
      y + h + 10 > p.y
    );
  }

  const top50 = words.slice(0, 45);
  top50.forEach((item, i) => {
    const size  = Math.round(10 + (item.count / maxCount) * 34);
    const color = palette[i % palette.length];
    ctx.font     = `${600 + (i < 10 ? 200 : 0)} ${size}px Inter`;
    ctx.fillStyle = color;
    const tw = ctx.measureText(item.word).width;
    const th = size;

    let x, y, tries = 0, found = false;
    while (tries < 120) {
      x = Math.random() * (W - tw - 20) + 10;
      y = Math.random() * (H - th - 10) + th;
      if (!overlaps(x, y - th, tw, th)) {
        found = true; break;
      }
      tries++;
    }
    if (!found) return;
    placed.push({ x, y: y - th, w: tw, h: th });

    ctx.globalAlpha = 0.6 + (item.count / maxCount) * 0.4;
    ctx.fillText(item.word, x, y);
    ctx.globalAlpha = 1;
  });
}

// ── HOURS ───────────────────────────────────────────────
function renderHours(hours) {
  const section = $('hours-section');
  const grid    = $('hours-grid');
  if (!hours.length) { section.classList.add('hidden'); return; }
  section.classList.remove('hidden');
  grid.innerHTML = '';
  const today = new Date().toLocaleDateString('en-US', { weekday: 'long' });
  hours.forEach(h => {
    const div = el('div', 'hour-item');
    const isToday = h.day && h.day.toLowerCase().includes(today.toLowerCase().slice(0, 3));
    div.innerHTML = `
      <span class="hour-day" style="${isToday ? 'color:var(--accent-cyan)' : ''}">${h.day}</span>
      <span class="hour-time">${h.hours}</span>
    `;
    grid.appendChild(div);
  });
}

// ── REVIEWS ─────────────────────────────────────────────
function renderReviews(reviews) {
  const list = $('reviews-list');
  list.innerHTML = '';
  $('review-badge').textContent = reviews.length;
  $('review-badge-2');

  if (!reviews.length) {
    list.innerHTML = '<p style="color:#475569;font-size:.88rem;text-align:center;padding:2rem">No reviews found. Try a different business or location.</p>';
    return;
  }

  reviews.forEach((r, i) => {
    const card = el('div', 'review-card');
    card.style.animationDelay = (i * 40) + 'ms';

    const initial = (r.author || 'A')[0].toUpperCase();
    const color   = AVATAR_COLORS[(r.author?.charCodeAt(0) || 0) % AVATAR_COLORS.length];
    const stars   = r.rating ? '⭐'.repeat(r.rating) + '☆'.repeat(5 - r.rating) : '—';
    const sTag    = sentimentTagHTML(r.sentiment?.label);

    card.innerHTML = `
      <div class="review-top">
        <div class="review-avatar" style="background:linear-gradient(135deg,${color},${AVATAR_COLORS[(i+3)%AVATAR_COLORS.length]})">${initial}</div>
        <div class="review-meta">
          <div class="review-author">${escHtml(r.author || 'Anonymous')}</div>
          <div class="review-date">${escHtml(r.date || '')}</div>
        </div>
        <div class="review-stars">${stars}</div>
        ${sTag}
      </div>
      <div class="review-text">${escHtml(r.text || 'No review text.')}</div>
    `;
    list.appendChild(card);
  });
}

function sentimentTagHTML(label) {
  const map = {
    'Positive': ['tag-pos', '✓ Positive'],
    'Negative': ['tag-neg', '✗ Negative'],
    'Mixed':    ['tag-mix', '~ Mixed'],
    'Neutral':  ['tag-neu', '· Neutral'],
  };
  const [cls, txt] = map[label] || ['tag-neu', '· Unknown'];
  return `<span class="sentiment-tag ${cls}">${txt}</span>`;
}

// ── REVIEW FILTERS ──────────────────────────────────────
function filterReviews(filter, btn) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');

  let filtered;
  switch (filter) {
    case 'all': filtered = all_reviews; break;
    case '5':   filtered = all_reviews.filter(r => r.rating === 5); break;
    case '4':   filtered = all_reviews.filter(r => r.rating === 4); break;
    case '3':   filtered = all_reviews.filter(r => r.rating === 3); break;
    case 'neg': filtered = all_reviews.filter(r => r.rating <= 2); break;
    case 'pos': filtered = all_reviews.filter(r => r.sentiment?.label === 'Positive'); break;
    default:    filtered = all_reviews;
  }
  renderReviews(filtered);
}

// ── EXPORT ──────────────────────────────────────────────
function exportData(format) {
  if (!scraped_data) return;

  if (format === 'json') {
    const blob = new Blob([JSON.stringify(scraped_data, null, 2)], { type: 'application/json' });
    downloadBlob(blob, `recon_${scraped_data.company}_${scraped_data.location}.json`);
  } else {
    const rows = [['Author','Date','Rating','Sentiment','Text']];
    (scraped_data.reviews || []).forEach(r => {
      rows.push([
        csvEsc(r.author), csvEsc(r.date), r.rating,
        csvEsc(r.sentiment?.label), csvEsc(r.text)
      ]);
    });
    const csv = rows.map(r => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    downloadBlob(blob, `recon_${scraped_data.company}_${scraped_data.location}.csv`);
  }
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a);
  a.click(); a.remove();
  URL.revokeObjectURL(url);
}

function csvEsc(str) {
  if (!str) return '""';
  return '"' + String(str).replace(/"/g, '""') + '"';
}

// ── ERROR TOAST ─────────────────────────────────────────
function showError(msg) {
  $('toast-msg').textContent = msg;
  $('error-toast').classList.remove('hidden');
  setTimeout(() => $('error-toast').classList.add('hidden'), 6000);
}
function hideToast() { $('error-toast').classList.add('hidden'); }

// ── UTILS ────────────────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
