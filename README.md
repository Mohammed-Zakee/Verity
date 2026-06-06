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

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-1.44+-45ba4b?style=for-the-badge&logo=playwright&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-purple?style=for-the-badge)

<br/>

</div>

---

## What is Verity?

**Verity** is a full-stack business intelligence scraper with a premium dark web UI. You give it any business name and location — it silently drives a headless browser to Google Maps, extracts everything public about that business, and renders a rich intelligence dashboard with charts, sentiment analysis, and competitive insights.

No API keys. No subscriptions. Just truth.

---

## Features

### Core Scraping
- **Business Identity** — Name, category, address, phone, website
- **Rating & Review Count** — Star rating and total review count
- **Opening Hours** — Full weekly schedule with today highlighted
- **Up to 50 Reviews** — Author, date, star rating, and full review text (auto-expands truncated reviews)

### 🧠 Unique Intelligence Features

| Feature | Description |
|---|---|
| **Sentiment Intelligence Engine** | Every review is scored Positive / Negative / Mixed / Neutral using a keyword NLP engine — rendered as a live animated donut chart and progress bars |
| **🚨 Red Flag Detector™** | Scans all 1–2★ reviews for the most repeated complaint words. Ranks them with a danger-meter so you instantly see the biggest issues with any business |
| **📈 Rating Timeline** | Groups reviews by approximate month and plots average rating over time — instantly reveals if a business is improving or in decline |
| **🎯 Theme Analysis** | Auto-categorizes review mentions into 6 themes (Service, Food/Product, Wait Time, Cleanliness, Value, Ambience) with a positive/negative breakdown per theme |
| **💬 Word Cloud** | Frequency-weighted word cloud rendered natively on `<canvas>` — no third-party library, just raw pixel rendering |
| **⬇ One-Click Export** | Export the full scraped dataset as **JSON** or **CSV** with a single click |

### UI
- Premium dark glassmorphism design with animated background orbs
- Animated progress bar with step indicators during scraping
- Review filtering by star rating or sentiment label
- Fully responsive layout

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11, Flask 3.0 |
| **Scraping Engine** | Playwright (headless Chromium) |
| **NLP / Analysis** | Custom keyword-based sentiment engine (no API key needed) |
| **Frontend** | HTML5, Vanilla CSS (glassmorphism), Vanilla JavaScript |
| **Charts** | Chart.js 4 (CDN) |
| **Word Cloud** | Custom `<canvas>` renderer |
| **Fonts** | Inter + JetBrains Mono (Google Fonts) |

---

## Project Structure

```
Verity/
├── app.py                  ← Flask backend + Playwright scraper + Sentiment Engine
├── requirements.txt        ← Python dependencies
├── templates/
│   └── index.html          ← Single-page application UI
└── static/
    ├── style.css           ← Glassmorphism dark design system
    └── app.js              ← Charts, word cloud, filtering, export logic
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- pip

### 1. Clone the repository

```bash
git clone https://github.com/Mohammed-Zakee/Verity.git
cd Verity
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Install the Playwright browser (Chromium)

```bash
python -m playwright install chromium
```

### 4. Run the app

```bash
python app.py
```

### 5. Open in your browser

```
http://127.0.0.1:5000
```

---

## How to Use

1. Enter a **Business Name** — e.g. `Starbucks`, `McDonald's`, `Tesla Service Center`
2. Enter a **Location** — e.g. `New York`, `London`, `Dubai`
3. Click **⚡ Run Verity**
4. Wait ~20–40 seconds while the headless browser scrapes Google Maps
5. Explore the intelligence dashboard:
   - View the Sentiment Intelligence donut chart
   - Check the Red Flag Detector™ for recurring complaints
   - Analyze the Rating Timeline to spot trends
   - Browse Theme Analysis to see what customers talk about most
   - Filter reviews by star rating or sentiment
   - Export all data as JSON or CSV

---

## How the Sentiment Engine Works

Verity uses a zero-dependency, keyword-based NLP engine — no OpenAI, no cloud APIs.

1. Each review text is tokenized into individual words
2. Words are matched against curated **positive** and **negative** dictionaries (80+ words each)
3. A sentiment score is computed: `positive_hits / (positive_hits + negative_hits)`
4. Labels are assigned: `≥ 0.65` → Positive, `≤ 0.35` → Negative, otherwise Mixed
5. Theme keywords map each review to up to 6 business topics
6. The Red Flag Detector aggregates complaint words only from 1–2★ reviews

---

## Screenshots

> *Run the app and scrape any business to see the full dashboard in action.*

---

## Notes & Limitations

- Verity scrapes **publicly available** data from Google Maps. It does not bypass any authentication or access private information.
- Scrape responsibly. Excessive automated requests may be rate-limited by Google.
- Review count displayed is the count of reviews **scraped** (up to 50), not the total on Google Maps.
- The sentiment engine is keyword-based and works best on English-language reviews.
- Opening hours may not always be available depending on how the business has configured their listing.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with ⚡ — *Because every business has a truth worth knowing.*

</div>
