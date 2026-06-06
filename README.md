<div align="center">

<br/>

```
 ██╗   ██╗███████╗██████╗ ██╗████████╗██╗   ██╗
 ██║   ██║██╔════╝██╔══██╗██║╚══██╔══╝╚██╗ ██╔╝
 ██║   ██║█████╗  ██████╔╝██║   ██║    ╚████╔╝ 
 ╚██╗ ██╔╝██╔══╝  ██╔══██╗██║   ██║     ╚██╔╝  
  ╚████╔╝ ███████╗██║  ██║██║   ██║      ██║   
   ╚═══╝  ╚══════╝╚═╝  ╚═╝╚═╝   ╚═╝      ╚═╝   
```

### **Business Intelligence, Redefined.**

*Give Verity a company name and location. It tells you everything.*

<br/>

![Next.js](https://img.shields.io/badge/Next.js-14-black?style=for-the-badge&logo=next.js)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)
![Vercel](https://img.shields.io/badge/Vercel-Frontend-black?style=for-the-badge&logo=vercel)
![Railway](https://img.shields.io/badge/Railway-Backend-8B5CF6?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-purple?style=for-the-badge)

<br/>

</div>

---

## Architecture

```
┌─────────────────────────┐       ┌──────────────────────────────┐
│   FRONTEND  (Vercel)    │ ────▶ │   BACKEND API  (Railway)     │
│                         │       │                              │
│   Next.js 14            │       │   Flask + Playwright         │
│   Chart.js charts       │◀───── │   SerpAPI scraping           │
│   Canvas word cloud     │       │   Hugging Face AI sentiment  │
│   4-format download     │       │   Red Flag Detector          │
│                         │       │   Theme Analysis Engine      │
│   vercel.com            │       │   railway.app                │
└─────────────────────────┘       └──────────────────────────────┘
```

---

## What Verity Does

Enter any business name and location. Verity:

1. **Scrapes Google Maps** via SerpAPI — business name, address, phone, website, rating, hours, up to 50 reviews
2. **Analyzes every review** with Hugging Face RoBERTa AI model (falls back to keyword NLP)
3. **Renders a full intelligence dashboard** with charts, word clouds, and theme breakdowns
4. **Lets you export** in 4 formats — JSON, CSV, Excel, PDF

---

## Unique Features

| Feature | Description |
|---|---|
| 🧠 **Sentiment Intelligence Engine** | AI-powered (Hugging Face RoBERTa) sentiment per review — Positive / Negative / Mixed / Neutral — shown as a live donut chart |
| 🚨 **Red Flag Detector™** | Scans 1–2★ reviews for the most repeated complaint words and shows a ranked danger-meter |
| 📈 **Rating Timeline** | Plots average rating month-by-month — reveals if a business is improving or declining |
| 🎯 **Theme Analysis** | Auto-categorizes reviews into 6 themes (Service, Food, Wait Time, Cleanliness, Value, Ambience) with positive/negative breakdown |
| 💬 **Word Cloud** | Frequency-weighted word cloud rendered natively on `<canvas>` — no third-party library |
| ⬇ **4-Format Export** | Download the full dataset as **JSON**, **CSV**, **Excel** (multi-sheet), or a formatted **PDF report** |

---

## Project Structure

```
Verity/
├── frontend/               ← Next.js app → deploy to Vercel
│   ├── app/
│   │   ├── page.tsx        ← Full dashboard UI
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── next.config.js
│   ├── vercel.json
│   └── package.json
│
├── backend/                ← Flask API → deploy to Railway
│   ├── app.py              ← Scraper + Sentiment Engine + REST API
│   ├── requirements.txt
│   ├── Procfile
│   ├── railway.json
│   └── runtime.txt
│
└── README.md
```

---

## Local Development

### Backend

```bash
cd backend
pip install -r requirements.txt
python -m playwright install chromium

# Optional — set API keys for full functionality
export SERP_API_KEY=your_serpapi_key
export HF_API_KEY=your_huggingface_token

python app.py
# Runs at http://localhost:5000
```

### Frontend

```bash
cd frontend
npm install

# Point to your local backend
echo "NEXT_PUBLIC_API_URL=http://localhost:5000" > .env.local

npm run dev
# Runs at http://localhost:3000
```

---

## Production Deployment

### Step 1 — Deploy Backend to Railway

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
2. Select the `Verity` repo → set **Root Directory** to `/backend`
3. Add environment variables:
   ```
   SERP_API_KEY=your_serpapi_key        # serpapi.com — 100 free searches/month
   HF_API_KEY=your_huggingface_token    # huggingface.co — free
   FRONTEND_URL=https://your-app.vercel.app
   ```
4. Railway will auto-detect the `Procfile` and install Playwright Chromium
5. Copy the generated public URL (e.g. `https://verity-backend.railway.app`)

### Step 2 — Deploy Frontend to Vercel

1. Go to [vercel.com](https://vercel.com) → **New Project** → **Import from GitHub**
2. Select `Verity` → set **Root Directory** to `/frontend`
3. Add environment variable:
   ```
   NEXT_PUBLIC_API_URL=https://verity-backend.railway.app
   ```
4. Click **Deploy** — done ✅

---

## API Keys

| Key | Where to Get | Free Tier |
|---|---|---|
| `SERP_API_KEY` | [serpapi.com](https://serpapi.com) | 100 searches/month |
| `HF_API_KEY` | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) | Free inference API |

> Without `SERP_API_KEY`, the backend falls back to Playwright (works locally, not on Railway).  
> Without `HF_API_KEY`, sentiment analysis uses the built-in keyword engine (no API needed).

---

## Download Formats

| Format | Content |
|---|---|
| **JSON** | Full scraped data object including all analysis |
| **CSV** | All reviews with author, date, rating, sentiment, AI source, text |
| **Excel (.xlsx)** | 4 sheets: Overview, Reviews, Themes, Rating Timeline |
| **PDF** | Formatted report with business summary, sentiment breakdown, red flags, and reviews |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Vanilla CSS |
| Charts | Chart.js 4 + react-chartjs-2 |
| Word Cloud | Custom `<canvas>` renderer |
| PDF Export | jsPDF |
| Excel Export | SheetJS (xlsx) |
| Backend | Python 3.11, Flask 3.0, Gunicorn |
| Scraping | SerpAPI (Google Maps) + Playwright fallback |
| AI Sentiment | Hugging Face RoBERTa + keyword NLP fallback |
| Deployment | Vercel (frontend) + Railway (backend) |

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with ⚡ — *Because every business has a truth worth knowing.*

</div>
