'use client'
// Verity Frontend — connects to self-built Playwright scraper + self-built NLP engine

import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Chart as ChartJS,
  ArcElement, Tooltip, Legend,
  CategoryScale, LinearScale, PointElement, LineElement, Filler
} from 'chart.js'
import { Doughnut, Line } from 'react-chartjs-2'

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, PointElement, LineElement, Filler)

// ── Types ─────────────────────────────────────────────────────────
interface Review {
  author: string
  date: string
  rating: number | null
  text: string
  sentiment: { label: string; score: number; source?: string }
  avatar?: string
}

interface ScrapedData {
  company: string
  location: string
  name: string
  address: string
  phone: string
  website: string
  category: string
  rating: number | null
  review_count: number | null
  hours: Array<{ day: string; hours: string }>
  reviews: Review[]
  sentiment_summary: {
    positive_pct: number
    negative_pct: number
    labels: { Positive: number; Negative: number; Mixed: number; Neutral: number }
  }
  themes: Record<string, { mentions: number; positive: number; negative: number }>
  red_flags: Array<{ word: string; count: number }>
  word_freq: Array<{ word: string; count: number }>
  timeline: Array<{ month: string; avg_rating: number; count: number }>
  scraped_at: string
}

// ── Constants ──────────────────────────────────────────────────────
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'

const AVATAR_COLORS = [
  '#6366f1','#a855f7','#ec4899','#ef4444','#f97316',
  '#eab308','#22c55e','#14b8a6','#0ea5e9','#3b82f6'
]

const PROGRESS_STEPS = ['🔍 Locating', '📥 Extracting', '🧠 Analyzing', '📊 Rendering']

// ── Helpers ────────────────────────────────────────────────────────
function avatarColor(name: string, idx = 0) {
  return AVATAR_COLORS[((name?.charCodeAt(0) || 0) + idx) % AVATAR_COLORS.length]
}
function starsStr(rating: number | null) {
  if (!rating) return '—'
  return '⭐'.repeat(Math.round(rating)) + '☆'.repeat(5 - Math.round(rating))
}
function esc(s: string) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
}
function sentimentTagClass(label: string) {
  return { Positive: 'tag-pos', Negative: 'tag-neg', Mixed: 'tag-mix', Neutral: 'tag-neu' }[label] ?? 'tag-neu'
}
function sentimentTagEmoji(label: string) {
  return { Positive: '✓ Positive', Negative: '✗ Negative', Mixed: '~ Mixed', Neutral: '· Neutral' }[label] ?? label
}

// ── Download helpers ───────────────────────────────────────────────
async function downloadJSON(data: ScrapedData) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url; a.download = `verity_${data.company}_${data.location}.json`
  a.click(); URL.revokeObjectURL(url)
}

async function downloadCSV(data: ScrapedData) {
  const rows = [['Author','Date','Rating','Sentiment','AI Source','Text']]
  data.reviews.forEach(r => {
    rows.push([
      `"${(r.author||'').replace(/"/g,'""')}"`,
      `"${(r.date||'').replace(/"/g,'""')}"`,
      String(r.rating ?? ''),
      r.sentiment?.label ?? '',
      r.sentiment?.source ?? 'keyword',
      `"${(r.text||'').replace(/"/g,'""')}"`,
    ])
  })
  const blob = new Blob([rows.map(r => r.join(',')).join('\n')], { type: 'text/csv' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url; a.download = `verity_${data.company}_reviews.csv`
  a.click(); URL.revokeObjectURL(url)
}

async function downloadExcel(data: ScrapedData) {
  const XLSX = await import('xlsx')
  const wb   = XLSX.utils.book_new()

  // Sheet 1 — Overview
  const overview = [
    ['Verity Business Intelligence Report'],
    ['Generated', data.scraped_at],
    [],
    ['Business Name', data.name],
    ['Category',     data.category],
    ['Address',      data.address],
    ['Phone',        data.phone],
    ['Website',      data.website],
    ['Rating',       data.rating],
    ['Review Count', data.review_count],
    [],
    ['Sentiment', 'Count'],
    ['Positive',  data.sentiment_summary.labels.Positive],
    ['Negative',  data.sentiment_summary.labels.Negative],
    ['Mixed',     data.sentiment_summary.labels.Mixed],
    ['Neutral',   data.sentiment_summary.labels.Neutral],
  ]
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(overview), 'Overview')

  // Sheet 2 — Reviews
  const reviewRows = [['Author','Date','Rating','Sentiment','AI Source','Text']]
  data.reviews.forEach(r => reviewRows.push([r.author, r.date, String(r.rating??''), r.sentiment?.label, r.sentiment?.source??'keyword', r.text]))
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(reviewRows), 'Reviews')

  // Sheet 3 — Themes
  const themeRows = [['Theme','Mentions','Positive','Negative']]
  Object.entries(data.themes).forEach(([t,v]) => themeRows.push([t, String(v.mentions), String(v.positive), String(v.negative)]))
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(themeRows), 'Themes')

  // Sheet 4 — Rating Timeline
  const tlRows = [['Month','Avg Rating','Review Count']]
  data.timeline.forEach(t => tlRows.push([t.month, String(t.avg_rating), String(t.count)]))
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(tlRows), 'Timeline')

  XLSX.writeFile(wb, `verity_${data.company}.xlsx`)
}

async function downloadPDF(data: ScrapedData) {
  const { jsPDF } = await import('jspdf')
  const doc = new jsPDF()
  const pageW = doc.internal.pageSize.getWidth()

  // Title
  doc.setFillColor(5, 8, 17)
  doc.rect(0, 0, pageW, 40, 'F')
  doc.setTextColor(0, 229, 255)
  doc.setFontSize(22); doc.setFont('helvetica', 'bold')
  doc.text('VERITY', 14, 18)
  doc.setFontSize(10); doc.setTextColor(148, 163, 184)
  doc.text('Business Intelligence Report', 14, 27)
  doc.setFontSize(8)
  doc.text(`Generated: ${new Date(data.scraped_at).toLocaleString()}`, 14, 35)

  // Business info
  doc.setTextColor(240, 244, 255)
  doc.setFontSize(16); doc.setFont('helvetica','bold')
  doc.text(data.name || data.company, 14, 55)
  doc.setFontSize(9); doc.setFont('helvetica','normal')
  doc.setTextColor(148, 163, 184)
  doc.text(`Category: ${data.category || 'N/A'}`, 14, 63)
  doc.text(`Address: ${data.address || 'N/A'}`, 14, 70)
  doc.text(`Phone: ${data.phone || 'N/A'}`, 14, 77)
  doc.text(`Website: ${data.website || 'N/A'}`, 14, 84)

  // Rating
  if (data.rating) {
    doc.setTextColor(251, 191, 36)
    doc.setFontSize(28); doc.setFont('helvetica','bold')
    doc.text(String(data.rating), pageW - 40, 65)
    doc.setFontSize(9); doc.setTextColor(148,163,184); doc.setFont('helvetica','normal')
    doc.text(`${data.review_count ?? data.reviews.length} reviews`, pageW - 45, 75)
  }

  // Sentiment
  let y = 100
  doc.setDrawColor(255,255,255,20)
  doc.line(14, y-5, pageW-14, y-5)
  doc.setTextColor(0,229,255); doc.setFontSize(11); doc.setFont('helvetica','bold')
  doc.text('Sentiment Intelligence', 14, y)
  y += 8
  const sl = data.sentiment_summary.labels
  const total = sl.Positive + sl.Negative + sl.Mixed + sl.Neutral || 1
  ;[['Positive', sl.Positive, [34,211,167]], ['Negative', sl.Negative, [248,113,113]], ['Mixed', sl.Mixed, [251,191,36]], ['Neutral', sl.Neutral, [148,163,184]]].forEach(([label, count, color]) => {
    const pct = Math.round((count as number)/total*100)
    doc.setTextColor(240,244,255); doc.setFont('helvetica','normal'); doc.setFontSize(9)
    doc.text(`${label}:`, 14, y)
    doc.setFillColor(...(color as [number,number,number]))
    doc.rect(40, y-4, pct*1.2, 5, 'F')
    doc.text(`${count} (${pct}%)`, 44 + pct*1.2, y)
    y += 9
  })

  // Red Flags
  if (data.red_flags.length) {
    y += 5
    doc.line(14, y-5, pageW-14, y-5)
    doc.setTextColor(248,113,113); doc.setFontSize(11); doc.setFont('helvetica','bold')
    doc.text('🚨 Red Flag Detector', 14, y); y += 8
    data.red_flags.slice(0,5).forEach(f => {
      doc.setTextColor(240,244,255); doc.setFont('helvetica','normal'); doc.setFontSize(9)
      doc.text(`• ${f.word}: mentioned ${f.count}× in negative reviews`, 14, y); y += 7
    })
  }

  // Reviews
  y += 8
  if (y > 240) { doc.addPage(); y = 20 }
  doc.line(14, y-5, pageW-14, y-5)
  doc.setTextColor(0,229,255); doc.setFontSize(11); doc.setFont('helvetica','bold')
  doc.text(`Reviews (${data.reviews.length} scraped)`, 14, y); y += 8
  data.reviews.slice(0, 15).forEach(r => {
    if (y > 270) { doc.addPage(); y = 20 }
    doc.setTextColor(240,244,255); doc.setFont('helvetica','bold'); doc.setFontSize(8.5)
    doc.text(`${r.author}  ·  ${r.date}  ·  ${'★'.repeat(r.rating||0)}  ·  [${r.sentiment?.label}]`, 14, y); y += 6
    doc.setTextColor(148,163,184); doc.setFont('helvetica','normal'); doc.setFontSize(8)
    const lines = doc.splitTextToSize(r.text || 'No text', pageW - 28)
    lines.slice(0,3).forEach((line: string) => { doc.text(line, 14, y); y += 5 })
    y += 3
  })

  doc.save(`verity_${data.company}_report.pdf`)
}

// ═══════════════════════════════════════════════════════════════════
// MAIN PAGE COMPONENT
// ═══════════════════════════════════════════════════════════════════
export default function HomePage() {
  const [company,   setCompany]   = useState('')
  const [location,  setLocation]  = useState('')
  const [loading,   setLoading]   = useState(false)
  const [progress,  setProgress]  = useState(0)
  const [stepIdx,   setStepIdx]   = useState(0)
  const [data,      setData]      = useState<ScrapedData | null>(null)
  const [error,     setError]     = useState('')
  const [filter,    setFilter]    = useState('all')
  const wcRef       = useRef<HTMLCanvasElement>(null)
  const progressRef = useRef<NodeJS.Timeout | null>(null)

  // ── Progress animation ─────────────────────────────────────────
  const startProgress = useCallback(() => {
    setProgress(0); setStepIdx(0)
    let pct = 0
    progressRef.current = setInterval(() => {
      pct += Math.random() * 1.2
      if (pct > 85) pct = 85
      setProgress(pct)
      if (pct > 20) setStepIdx(1)
      if (pct > 50) setStepIdx(2)
      if (pct > 75) setStepIdx(3)
    }, 350)
  }, [])

  const stopProgress = useCallback((success: boolean) => {
    if (progressRef.current) clearInterval(progressRef.current)
    if (success) {
      setProgress(100); setStepIdx(4)
      setTimeout(() => setLoading(false), 700)
    } else {
      setLoading(false); setProgress(0)
    }
  }, [])

  // ── Submit ─────────────────────────────────────────────────────
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!company.trim() || !location.trim()) return
    setLoading(true); setData(null); setError(''); setFilter('all')
    startProgress()
    try {
      const res  = await fetch(`${API_URL}/api/scrape`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company: company.trim(), location: location.trim() }),
      })
      const json = await res.json()
      if (!res.ok || json.error) throw new Error(json.error || 'Scrape failed')
      setData(json)
      stopProgress(true)
    } catch (err: any) {
      setError(err.message || 'Unknown error')
      stopProgress(false)
    }
  }

  // ── Word cloud ─────────────────────────────────────────────────
  useEffect(() => {
    if (!data?.word_freq?.length || !wcRef.current) return
    const canvas = wcRef.current
    const ctx    = canvas.getContext('2d')!
    const W = canvas.width, H = canvas.height
    ctx.clearRect(0, 0, W, H)
    const words  = data.word_freq
    const maxCt  = words[0]?.count || 1
    const pal    = ['#00e5ff','#a855f7','#ec4899','#22d3a7','#fbbf24','#f97316','#6366f1','#14b8a6']
    const placed: {x:number;y:number;w:number;h:number}[] = []
    const overlaps = (x:number,y:number,w:number,h:number) =>
      placed.some(p => x<p.x+p.w+10 && x+w+10>p.x && y<p.y+p.h+10 && y+h+10>p.y)
    words.slice(0,45).forEach((item,i) => {
      const size  = Math.round(10 + (item.count/maxCt)*34)
      ctx.font    = `${600+(i<10?200:0)} ${size}px Inter`
      ctx.fillStyle = pal[i%pal.length]
      const tw = ctx.measureText(item.word).width
      let x=0,y=0,tries=0,found=false
      while(tries<130){
        x = Math.random()*(W-tw-20)+10
        y = Math.random()*(H-size-10)+size
        if(!overlaps(x,y-size,tw,size)){found=true;break}
        tries++
      }
      if(!found)return
      placed.push({x,y:y-size,w:tw,h:size})
      ctx.globalAlpha = 0.55 + (item.count/maxCt)*0.45
      ctx.fillText(item.word,x,y)
      ctx.globalAlpha = 1
    })
  }, [data])

  // ── Filtered reviews ───────────────────────────────────────────
  const filteredReviews = (data?.reviews || []).filter(r => {
    if (filter === 'all') return true
    if (filter === '5') return r.rating === 5
    if (filter === '4') return r.rating === 4
    if (filter === '3') return r.rating === 3
    if (filter === 'neg') return (r.rating ?? 5) <= 2
    if (filter === 'pos') return r.sentiment?.label === 'Positive'
    return true
  })

  // ── Chart configs ──────────────────────────────────────────────
  const donutData = data ? {
    labels: ['Positive', 'Negative', 'Mixed', 'Neutral'],
    datasets: [{
      data: [data.sentiment_summary.labels.Positive, data.sentiment_summary.labels.Negative,
             data.sentiment_summary.labels.Mixed,    data.sentiment_summary.labels.Neutral],
      backgroundColor: ['#22d3a7','#f87171','#fbbf24','#475569'],
      borderColor: 'transparent', borderWidth: 0, hoverOffset: 6
    }]
  } : null

  const timelineData = data?.timeline?.length ? {
    labels: data.timeline.map(t => t.month),
    datasets: [{
      label: 'Avg Rating',
      data:  data.timeline.map(t => t.avg_rating),
      borderColor: '#00e5ff', backgroundColor: 'rgba(0,229,255,0.07)',
      borderWidth: 2.5, pointBackgroundColor: '#00e5ff',
      pointRadius: 5, pointHoverRadius: 8, tension: 0.4, fill: true
    }]
  } : null

  const donutOptions = {
    cutout: '72%', plugins: { legend: { display: false }, tooltip: {
      callbacks: { label: (c: any) => ` ${c.label}: ${c.raw} reviews` }
    }},
    animation: { duration: 1000 }
  } as const

  const lineOptions = {
    responsive: true, maintainAspectRatio: false,
    scales: {
      y: { min: 1, max: 5, ticks: { color: '#475569', stepSize: 1 }, grid: { color: 'rgba(255,255,255,0.05)' } },
      x: { ticks: { color: '#475569', maxRotation: 30 }, grid: { color: 'rgba(255,255,255,0.04)' } }
    },
    plugins: { legend: { display: false }, tooltip: {
      backgroundColor: 'rgba(8,13,26,0.9)', borderColor: 'rgba(255,255,255,0.1)', borderWidth: 1,
      callbacks: { label: (c: any) => ` ${c.parsed.y.toFixed(2)} ★  (${data?.timeline[c.dataIndex]?.count} reviews)` }
    }},
    animation: { duration: 1200 }
  } as const

  // ── Sentiment bar widths ───────────────────────────────────────
  const sentTotal = data ? (data.sentiment_summary.labels.Positive + data.sentiment_summary.labels.Negative +
    data.sentiment_summary.labels.Mixed + data.sentiment_summary.labels.Neutral) || 1 : 1
  const sentBarW = (n: number) => `${Math.round(n / sentTotal * 100)}%`

  return (
    <>
      {/* BG orbs */}
      <div className="bg-orbs">
        <div className="orb orb-1" />
        <div className="orb orb-2" />
        <div className="orb orb-3" />
      </div>

      {/* Header */}
      <header className="site-header">
        <div className="header-inner">
          <a className="logo" href="/">
            <span className="logo-hex">⬡</span>
            <span className="logo-text">VERITY</span>
            <span className="logo-badge">AI</span>
          </a>
          <span className="header-tag">Business Intelligence</span>
        </div>
      </header>

      <main className="main-wrap">

        {/* ── SEARCH ─────────────────────────────────────────── */}
        <section className="glass search-wrap">
          <div className="search-headline">
            <h1>Drop a business.<br /><span className="grad">We&apos;ll tell you everything.</span></h1>
            <p className="search-sub">AI-powered scraping · Sentiment analysis · Red flag detection · Multi-format export</p>
          </div>

          <form className="search-form" onSubmit={handleSubmit}>
            <div className="input-grp">
              <label htmlFor="company">Business Name</label>
              <div className="input-rel">
                <span className="input-ico">🏢</span>
                <input id="company" type="text" placeholder="e.g. Starbucks, Tesla, McDonald's…"
                  value={company} onChange={e => setCompany(e.target.value)} required />
              </div>
            </div>
            <div className="input-grp">
              <label htmlFor="location">Location</label>
              <div className="input-rel">
                <span className="input-ico">📍</span>
                <input id="location" type="text" placeholder="e.g. New York, London, Dubai…"
                  value={location} onChange={e => setLocation(e.target.value)} required />
              </div>
            </div>
            <button type="submit" className="btn-run" disabled={loading}>
              <span>{loading ? '⏳' : '⚡'}</span>
              <span>{loading ? 'Running…' : 'Run Verity'}</span>
            </button>
          </form>

          {/* Progress */}
          {loading && (
            <div className="progress-area">
              <div className="prog-track">
                <div className="prog-fill" style={{ width: `${progress}%` }} />
              </div>
              <div className="prog-steps">
                {PROGRESS_STEPS.map((s, i) => (
                  <span key={s} className={`step-item ${i < stepIdx ? 'done' : i === stepIdx ? 'active' : ''}`}>{s}</span>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* ── RESULTS ────────────────────────────────────────── */}
        {data && (
          <>
            {/* IDENTITY */}
            <section className="glass identity">
              <div className="id-left">
                <div className="biz-avatar" style={{ background: `linear-gradient(135deg, ${avatarColor(data.name||'',0)}, ${avatarColor(data.name||'',3)})` }}>
                  {(data.name||data.company||'?').split(' ').slice(0,2).map(w=>w[0]?.toUpperCase()||'').join('')}
                </div>
                <div>
                  <div className="biz-name">{data.name || data.company}</div>
                  <div className="biz-cat">{data.category}</div>
                  <div className="biz-meta">
                    {data.address  && <span className="meta-item">📍 {data.address}</span>}
                    {data.phone    && <span className="meta-item">📞 {data.phone}</span>}
                    {data.website  && <span className="meta-item">🌐 {data.website}</span>}
                  </div>
                </div>
              </div>
              <div className="id-right">
                <div className="rating-big">
                  <span className="rating-num">{data.rating?.toFixed(1) || '—'}</span>
                  <div className="stars">{starsStr(data.rating)}</div>
                  <div className="review-ct">{data.review_count ? data.review_count.toLocaleString() + ' reviews' : `${data.reviews.length} scraped`}</div>
                </div>
                <div className="dl-row">
                  <button className="btn-dl" onClick={() => downloadJSON(data)}>⬇ JSON</button>
                  <button className="btn-dl" onClick={() => downloadCSV(data)}>⬇ CSV</button>
                  <button className="btn-dl excel" onClick={() => downloadExcel(data)}>⬇ Excel</button>
                  <button className="btn-dl pdf"   onClick={() => downloadPDF(data)}>⬇ PDF</button>
                </div>
              </div>
            </section>

            {/* ROW 1 — Sentiment + Red Flags */}
            <div className="cards-row">

              {/* SENTIMENT */}
              <section className="glass">
                <div className="card-head">
                  <span className="card-ico">🧠</span>
                  <h3>Sentiment Intelligence</h3>
                  <span className="badge-unique">UNIQUE</span>
                </div>
                <div className="sent-body">
                  <div className="donut-wrap">
                    {donutData && <Doughnut data={donutData} options={donutOptions} />}
                    <div className="donut-center">
                      <span className="donut-pct">{Math.round(data.sentiment_summary.labels.Positive / sentTotal * 100)}%</span>
                      <span className="donut-lbl">Positive</span>
                    </div>
                  </div>
                  <div className="sent-bars">
                    {[
                      ['😊 Positive', 'sbar-pos', data.sentiment_summary.labels.Positive],
                      ['😤 Negative', 'sbar-neg', data.sentiment_summary.labels.Negative],
                      ['😐 Mixed',    'sbar-mix', data.sentiment_summary.labels.Mixed],
                      ['😶 Neutral',  'sbar-neu', data.sentiment_summary.labels.Neutral],
                    ].map(([label, cls, count]) => (
                      <div key={String(label)} className="sbar">
                        <span className="sbar-label">{String(label)}</span>
                        <div className="sbar-track">
                          <div className={`sbar-fill ${cls}`} style={{ width: sentBarW(count as number) }} />
                        </div>
                        <span className="sbar-cnt">{String(count)}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <p style={{fontSize:'0.72rem',color:'#475569',marginTop:'1rem'}}>⚙ Powered by Verity&apos;s self-built NLP engine — no third-party AI</p>
              </section>

              {/* RED FLAGS */}
              <section className="glass">
                <div className="card-head">
                  <span className="card-ico">🚨</span>
                  <h3>Red Flag Detector™</h3>
                  <span className="badge-unique">UNIQUE</span>
                </div>
                {data.red_flags.length === 0
                  ? <p className="empty-msg">✅ No significant red flags detected.</p>
                  : data.red_flags.map((f, i) => {
                    const pct = Math.round(f.count / data.red_flags[0].count * 100)
                    return (
                      <div key={f.word} className="flag-item">
                        <span className="flag-word">⚠ {f.word}</span>
                        <div className="flag-track">
                          <div className="flag-fill" style={{ width: `${pct}%`, transitionDelay: `${i*80}ms` }} />
                        </div>
                        <span className="flag-cnt">{f.count}×</span>
                      </div>
                    )
                  })
                }
              </section>
            </div>

            {/* ROW 2 — Timeline + Themes */}
            <div className="cards-row">

              {/* TIMELINE */}
              <section className="glass">
                <div className="card-head">
                  <span className="card-ico">📈</span>
                  <h3>Rating Timeline</h3>
                  <span className="badge-unique">UNIQUE</span>
                </div>
                <div className="chart-wrap">
                  {timelineData
                    ? <Line data={timelineData} options={lineOptions} />
                    : <p className="empty-msg" style={{paddingTop:'4rem',textAlign:'center'}}>Not enough dated reviews for timeline.</p>}
                </div>
              </section>

              {/* THEMES */}
              <section className="glass">
                <div className="card-head">
                  <span className="card-ico">🎯</span>
                  <h3>Theme Analysis</h3>
                </div>
                {Object.entries(data.themes)
                  .sort((a,b) => b[1].mentions - a[1].mentions)
                  .filter(([,v]) => v.mentions > 0)
                  .map(([theme, v], i) => {
                    const posW = Math.round(v.positive / v.mentions * 100)
                    const negW = Math.round(v.negative / v.mentions * 100)
                    return (
                      <div key={theme} className="theme-item">
                        <div className="theme-hd">
                          <span className="theme-name">{theme}</span>
                          <span className="theme-ct">{v.mentions} mentions</span>
                        </div>
                        <div className="theme-track">
                          <div className="theme-pos" style={{ width: `${posW}%`, transitionDelay: `${i*60}ms` }} />
                          <div className="theme-neg" style={{ width: `${negW}%`, transitionDelay: `${i*60}ms` }} />
                        </div>
                      </div>
                    )
                  })}
              </section>
            </div>

            {/* WORD CLOUD */}
            <section className="glass">
              <div className="card-head">
                <span className="card-ico">💬</span>
                <h3>Review Word Cloud</h3>
                <span className="badge-unique">UNIQUE</span>
              </div>
              <canvas id="wc-canvas" ref={wcRef} width={900} height={280} />
            </section>

            {/* HOURS */}
            {data.hours.length > 0 && (
              <section className="glass">
                <div className="card-head">
                  <span className="card-ico">🕐</span>
                  <h3>Opening Hours</h3>
                </div>
                <div className="hours-grid">
                  {data.hours.map((h, i) => (
                    <div key={i} className="hour-item">
                      <span className="hour-day">{h.day}</span>
                      <span className="hour-time">{h.hours}</span>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* REVIEWS */}
            <section className="glass">
              <div className="card-head reviews-hd">
                <span className="card-ico">💬</span>
                <h3>Reviews <span className="rev-badge">{filteredReviews.length}</span></h3>
                <div className="filter-row">
                  {[['all','All'],['5','★5'],['4','★4'],['3','★3'],['neg','⚠ Low'],['pos','✓ Positive']].map(([f,l]) => (
                    <button key={f} className={`filter-btn ${filter===f?'active':''}`} onClick={() => setFilter(f)}>{l}</button>
                  ))}
                </div>
              </div>
              <div className="reviews-list">
                {filteredReviews.length === 0
                  ? <p className="empty-msg" style={{textAlign:'center',padding:'2rem'}}>No reviews match this filter.</p>
                  : filteredReviews.map((r, i) => (
                    <div key={i} className="rev-card" style={{ animationDelay: `${Math.min(i,20)*40}ms` }}>
                      <div className="rev-top">
                        <div className="rev-avi" style={{ background: `linear-gradient(135deg,${avatarColor(r.author||'',0)},${avatarColor(r.author||'',3)})` }}>
                          {(r.author||'A')[0].toUpperCase()}
                        </div>
                        <div className="rev-meta">
                          <div className="rev-author">{r.author || 'Anonymous'}</div>
                          <div className="rev-date">{r.date}</div>
                        </div>
                        <div className="rev-stars">{starsStr(r.rating)}</div>
                        <span className={`sent-tag ${sentimentTagClass(r.sentiment?.label)}`}>
                          {sentimentTagEmoji(r.sentiment?.label)}
                        </span>
                      </div>
                      <div className="rev-text">{r.text || 'No review text.'}</div>
                    </div>
                  ))
                }
              </div>
            </section>
          </>
        )}

        {/* ERROR TOAST */}
        {error && (
          <div className="toast">
            <span>⚠</span>
            <span>{error}</span>
          </div>
        )}

      </main>

      <footer>
        <p>Verity — Business Intelligence Scraper &nbsp;·&nbsp; Built with ⚡</p>
      </footer>
    </>
  )
}
