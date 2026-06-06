"""
Verity Backend API
==================
- Scrapes Google Maps via SerpAPI (serverless-safe) OR Playwright (local fallback)
- Sentiment analysis via Hugging Face Inference API with keyword fallback
- CORS-enabled for Vercel frontend
- Endpoints: POST /api/scrape, GET /api/health
"""

import os
import re
import json
import time
import asyncio
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

# ── CORS — allow Vercel frontend + local dev ──────────────────────────────────
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://*.vercel.app",
]
FRONTEND_URL = os.environ.get("FRONTEND_URL", "*")
CORS(app, origins=["*"], methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"])

# ── API KEYS (set as Railway env vars) ───────────────────────────────────────
SERP_API_KEY   = os.environ.get("SERP_API_KEY", "")
HF_API_KEY     = os.environ.get("HF_API_KEY", "")   # Hugging Face token
HF_MODEL       = "cardiffnlp/twitter-roberta-base-sentiment-latest"


# ─────────────────────────────────────────────────────────────────────────────
# SENTIMENT ENGINE
# ─────────────────────────────────────────────────────────────────────────────
POSITIVE_WORDS = {
    "amazing", "excellent", "fantastic", "great", "love", "loved", "wonderful",
    "best", "perfect", "awesome", "outstanding", "superb", "brilliant", "friendly",
    "helpful", "clean", "fast", "quick", "fresh", "delicious", "beautiful",
    "recommend", "recommended", "impressive", "exceptional", "fabulous", "happy",
    "pleased", "satisfied", "good", "nice", "pleasant", "enjoy", "enjoyed",
    "polite", "professional", "efficient", "tasty", "cozy", "comfortable",
    "stunning", "incredible", "brilliant", "spotless", "attentive", "generous"
}

NEGATIVE_WORDS = {
    "terrible", "awful", "horrible", "worst", "bad", "poor", "disgusting",
    "rude", "slow", "dirty", "cold", "stale", "overpriced", "expensive",
    "disappointed", "disappointing", "unprofessional", "unhelpful", "never",
    "avoid", "waste", "disgusted", "unacceptable", "mediocre", "bland",
    "soggy", "broken", "filthy", "ignored", "wrong", "mistake", "charged",
    "complaint", "complained", "problem", "issue", "wait", "waiting",
    "long", "forever", "disgusting", "nasty", "gross", "sick", "toxic"
}

THEME_KEYWORDS = {
    "Service":      ["service", "staff", "waiter", "waitress", "server", "manager",
                     "employee", "rude", "friendly", "helpful", "polite", "attentive", "ignored"],
    "Food/Product": ["food", "meal", "dish", "taste", "flavor", "fresh", "stale",
                     "delicious", "bland", "cold", "hot", "cooked", "quality", "portion", "product"],
    "Wait Time":    ["wait", "waiting", "slow", "fast", "quick", "minutes", "hours",
                     "long", "forever", "delay", "delayed", "rush"],
    "Cleanliness":  ["clean", "dirty", "filthy", "hygiene", "sanitary", "bathroom",
                     "restroom", "smell", "smelly", "tidy", "neat", "messy"],
    "Value":        ["price", "expensive", "cheap", "overpriced", "worth", "value",
                     "costly", "affordable", "money", "charge", "charged", "fee", "bill"],
    "Ambience":     ["atmosphere", "ambience", "vibe", "noise", "loud", "quiet",
                     "cozy", "comfortable", "crowded", "parking", "location", "decor", "music"]
}


def keyword_sentiment(text: str) -> dict:
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    pos = sum(1 for w in words if w in POSITIVE_WORDS)
    neg = sum(1 for w in words if w in NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return {"score": 0.5, "label": "Neutral", "positive": 0, "negative": 0, "source": "keyword"}
    score = pos / total
    label = "Positive" if score >= 0.65 else ("Negative" if score <= 0.35 else "Mixed")
    return {"score": round(score, 3), "label": label, "positive": pos, "negative": neg, "source": "keyword"}


def hf_sentiment(text: str) -> dict | None:
    """Call Hugging Face Inference API for sentiment. Returns None on failure."""
    if not HF_API_KEY or len(text.strip()) < 5:
        return None
    try:
        url = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        # Truncate to 512 chars (model limit)
        payload = {"inputs": text[:512], "options": {"wait_for_model": True}}
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code != 200:
            return None
        results = resp.json()
        if isinstance(results, list) and len(results) > 0:
            scores = results[0]
            # Model returns: label2=Positive, label0=Negative, label1=Neutral
            label_map = {"LABEL_2": "Positive", "LABEL_1": "Mixed", "LABEL_0": "Negative",
                         "positive": "Positive", "neutral": "Mixed", "negative": "Negative"}
            best = max(scores, key=lambda x: x["score"])
            label = label_map.get(best["label"].upper(), label_map.get(best["label"], "Neutral"))
            confidence = round(best["score"], 3)
            return {
                "score":    confidence if label == "Positive" else (1 - confidence if label == "Negative" else 0.5),
                "label":    label,
                "confidence": confidence,
                "source":   "huggingface",
                "positive": 1 if label == "Positive" else 0,
                "negative": 1 if label == "Negative" else 0
            }
    except Exception:
        return None


def analyze_sentiment(text: str) -> dict:
    hf = hf_sentiment(text)
    return hf if hf else keyword_sentiment(text)


def extract_themes(reviews: list) -> dict:
    theme_counts = {t: {"mentions": 0, "positive": 0, "negative": 0} for t in THEME_KEYWORDS}
    for review in reviews:
        text  = review.get("text", "").lower()
        words = set(re.findall(r'\b[a-zA-Z]+\b', text))
        label = review.get("sentiment", {}).get("label", "")
        for theme, keywords in THEME_KEYWORDS.items():
            if any(k in words for k in keywords):
                theme_counts[theme]["mentions"] += 1
                if label == "Positive": theme_counts[theme]["positive"] += 1
                elif label == "Negative": theme_counts[theme]["negative"] += 1
    return theme_counts


def detect_red_flags(reviews: list) -> list:
    freq = {}
    for review in reviews:
        if review.get("rating", 5) and review.get("rating", 5) <= 2:
            words = re.findall(r'\b[a-zA-Z]{4,}\b', review.get("text", "").lower())
            for w in words:
                if w in NEGATIVE_WORDS:
                    freq[w] = freq.get(w, 0) + 1
    return [{"word": w, "count": c} for w, c in sorted(freq.items(), key=lambda x: -x[1])[:8]]


def extract_word_frequency(reviews: list) -> list:
    STOP = {"the","a","an","and","or","but","in","on","at","to","for","of","is","was",
            "it","i","we","my","me","they","this","that","with","have","had","not","be",
            "are","were","our","us","he","she","his","her","its","by","as","if","so",
            "do","did","from","up","out","about","been","can","will","would","just",
            "there","then","than","your","you","very","also","get","got","all","has",
            "like","one","more","when","what","which","who","how","no","yes","well",
            "over","too","only","even","some","time","really","went","here","their",
            "place","back","good","great","nice","bad","very","much","came","come"}
    freq = {}
    for review in reviews:
        for w in re.findall(r'\b[a-zA-Z]{4,}\b', review.get("text", "").lower()):
            if w not in STOP:
                freq[w] = freq.get(w, 0) + 1
    return [{"word": w, "count": c} for w, c in sorted(freq.items(), key=lambda x: -x[1])[:50]]


def build_timeline(reviews: list) -> list:
    now = datetime.now()
    monthly = {}
    for review in reviews:
        date_str = review.get("date", "")
        try:
            if "month" in date_str:
                n = 1 if date_str.startswith("a") else int(re.search(r'\d+', date_str).group())
                m, y = now.month - n, now.year
                while m <= 0: m += 12; y -= 1
                key = f"{y}-{m:02d}"
            elif "year" in date_str:
                n = 1 if date_str.startswith("a") else int(re.search(r'\d+', date_str).group())
                key = f"{now.year - n}-{now.month:02d}"
            else:
                key = f"{now.year}-{now.month:02d}"
        except Exception:
            key = f"{now.year}-{now.month:02d}"
        r = review.get("rating")
        if r:
            if key not in monthly: monthly[key] = []
            monthly[key].append(r)
    return [{"month": k, "avg_rating": round(sum(v)/len(v), 2), "count": len(v)}
            for k, v in sorted(monthly.items())]


# ─────────────────────────────────────────────────────────────────────────────
# SERP API SCRAPER (works on Vercel serverless — no browser needed)
# ─────────────────────────────────────────────────────────────────────────────
def scrape_via_serpapi(company: str, location: str) -> dict:
    """
    Uses SerpAPI's Google Maps endpoint to get business data.
    Sign up at serpapi.com — 100 free searches/month.
    """
    base = {
        "company": company, "location": location,
        "scraped_at": datetime.now().isoformat(),
        "name": None, "address": None, "phone": None, "website": None,
        "category": None, "rating": None, "review_count": None,
        "hours": [], "photos": [], "reviews": [], "error": None
    }

    if not SERP_API_KEY:
        return {**base, "error": "SERP_API_KEY not set. Please configure it in Railway environment variables."}

    try:
        # Step 1 — Search for place
        search_resp = requests.get("https://serpapi.com/search", params={
            "engine":    "google_maps",
            "q":         f"{company} {location}",
            "api_key":   SERP_API_KEY,
            "type":      "search",
            "hl":        "en"
        }, timeout=30)
        search_data = search_resp.json()

        if "error" in search_data:
            return {**base, "error": search_data["error"]}

        places = search_data.get("local_results", [])
        if not places:
            return {**base, "error": f"No results found for '{company}' in '{location}'"}

        place = places[0]
        data_id = place.get("data_id", "")

        base["name"]         = place.get("title", company)
        base["address"]      = place.get("address", "")
        base["phone"]        = place.get("phone", "")
        base["website"]      = place.get("website", "")
        base["category"]     = place.get("type", "")
        base["rating"]       = place.get("rating")
        base["review_count"] = place.get("reviews")
        base["photos"]       = [p.get("thumbnail", "") for p in place.get("photos", [])[:6]]

        # Hours
        hours_raw = place.get("hours", [])
        if isinstance(hours_raw, list):
            base["hours"] = hours_raw
        elif isinstance(hours_raw, dict):
            base["hours"] = [{"day": k, "hours": v} for k, v in hours_raw.items()]

        # Step 2 — Get reviews via place details
        if data_id:
            reviews_resp = requests.get("https://serpapi.com/search", params={
                "engine":    "google_maps_reviews",
                "data_id":   data_id,
                "api_key":   SERP_API_KEY,
                "hl":        "en",
                "sort_by":   "newestFirst",
                "num":       50
            }, timeout=30)
            reviews_data = reviews_resp.json()
            raw_reviews  = reviews_data.get("reviews", [])

            for r in raw_reviews:
                text      = r.get("snippet", "") or r.get("extracted_snippet", {}).get("original", "")
                rating    = r.get("rating")
                sentiment = analyze_sentiment(text)
                base["reviews"].append({
                    "author":    r.get("user", {}).get("name", "Anonymous"),
                    "date":      r.get("date", ""),
                    "rating":    rating,
                    "text":      text,
                    "sentiment": sentiment,
                    "avatar":    r.get("user", {}).get("thumbnail", "")
                })

    except requests.exceptions.Timeout:
        base["error"] = "Request timed out. Try again."
    except Exception as e:
        base["error"] = str(e)

    return base


# ─────────────────────────────────────────────────────────────────────────────
# PLAYWRIGHT FALLBACK (local development only)
# ─────────────────────────────────────────────────────────────────────────────
def scrape_via_playwright(company: str, location: str) -> dict:
    """Playwright fallback — used locally when SERP_API_KEY is not set."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"error": "Playwright not installed. Set SERP_API_KEY for production use."}

    base = {
        "company": company, "location": location,
        "scraped_at": datetime.now().isoformat(),
        "name": company, "address": None, "phone": None, "website": None,
        "category": None, "rating": None, "review_count": None,
        "hours": [], "photos": [], "reviews": [], "error": None
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900}, locale="en-US"
        )
        page = context.new_page()
        try:
            query = f"{company} {location}".replace(" ", "+")
            page.goto(f"https://www.google.com/maps/search/{query}", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            first = page.locator('a[href*="/maps/place/"]').first
            if first.count() > 0:
                first.click()
                page.wait_for_timeout(3000)

            # Name
            try: base["name"] = page.locator('h1.DUwDvf').first.inner_text(timeout=5000)
            except: pass

            # Category
            try: base["category"] = page.locator('button[jsaction*="category"]').first.inner_text(timeout=3000)
            except: pass

            # Rating
            try:
                rt = page.locator('div.F7nice span[aria-hidden="true"]').first.inner_text(timeout=4000)
                base["rating"] = float(rt.strip())
            except: pass

            # Review count
            try:
                ct = page.locator('div.F7nice span[aria-label*="review"]').first.inner_text(timeout=3000)
                m  = re.search(r'([\d,]+)', ct)
                if m: base["review_count"] = int(m.group(1).replace(",", ""))
            except: pass

            # Address
            try:
                a = page.locator('[data-item-id="address"]')
                if a.count(): base["address"] = a.first.inner_text(timeout=3000)
            except: pass

            # Phone
            try:
                ph = page.locator('[data-item-id*="phone"]')
                if ph.count(): base["phone"] = ph.first.inner_text(timeout=3000)
            except: pass

            # Website
            try:
                wb = page.locator('[data-item-id="authority"]')
                if wb.count(): base["website"] = wb.first.inner_text(timeout=3000)
            except: pass

            # Reviews tab
            try:
                rb = page.locator('button[aria-label*="review"]')
                if rb.count() == 0: rb = page.locator('div[role="tab"]:has-text("Reviews")')
                if rb.count(): rb.first.click(); page.wait_for_timeout(2000)
            except: pass

            # Sort newest
            try:
                sb = page.locator('button[aria-label*="Sort"]')
                if sb.count():
                    sb.first.click(); page.wait_for_timeout(800)
                    nw = page.locator('div[role="menuitemradio"]:has-text("Newest")')
                    if nw.count(): nw.first.click(); page.wait_for_timeout(2000)
            except: pass

            # Scroll for reviews
            rc = page.locator('div[role="main"]')
            for _ in range(8):
                try: rc.evaluate("el => el.scrollTop += 1200"); page.wait_for_timeout(700)
                except: break

            # Extract reviews
            for el in page.locator('div[data-review-id]').all()[:50]:
                try:
                    author = el.locator('.d4r55').first.inner_text(timeout=2000)
                    try:    date = el.locator('.rsqaWe').first.inner_text(timeout=2000)
                    except: date = ""
                    try:
                        ra  = el.locator('span[role="img"]').first.get_attribute("aria-label", timeout=2000)
                        rm  = re.search(r'(\d)', ra or "")
                        rv  = int(rm.group(1)) if rm else None
                    except: rv = None
                    try:
                        mb = el.locator('button.w8nwRe')
                        if mb.count(): mb.click(); page.wait_for_timeout(300)
                        text = el.locator('.wiI7pd').first.inner_text(timeout=2000)
                    except: text = ""
                    base["reviews"].append({
                        "author": author.strip(), "date": date.strip(),
                        "rating": rv, "text": text.strip(),
                        "sentiment": analyze_sentiment(text), "avatar": ""
                    })
                except: continue
        except Exception as e:
            base["error"] = str(e)
        finally:
            browser.close()
    return base


def post_process(data: dict) -> dict:
    reviews = data.get("reviews", [])
    labels  = {"Positive": 0, "Negative": 0, "Mixed": 0, "Neutral": 0}
    for r in reviews:
        l = r.get("sentiment", {}).get("label", "Neutral")
        labels[l] = labels.get(l, 0) + 1
    total = sum(labels.values()) or 1
    pos_p = round(labels["Positive"] / total * 100, 1)
    neg_p = round(labels["Negative"] / total * 100, 1)
    data["sentiment_summary"] = {
        "positive_pct": pos_p, "negative_pct": neg_p,
        "neutral_pct":  round(100 - pos_p - neg_p, 1),
        "labels": labels
    }
    data["themes"]    = extract_themes(reviews)
    data["red_flags"] = detect_red_flags(reviews)
    data["word_freq"] = extract_word_frequency(reviews)
    data["timeline"]  = build_timeline(reviews)
    return data


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "serp_api": bool(SERP_API_KEY),
        "hf_api":   bool(HF_API_KEY),
        "version":  "2.0.0"
    })


@app.route("/api/scrape", methods=["POST", "OPTIONS"])
def scrape():
    if request.method == "OPTIONS":
        return jsonify({"ok": True})

    body     = request.get_json() or {}
    company  = (body.get("company") or "").strip()
    location = (body.get("location") or "").strip()

    if not company or not location:
        return jsonify({"error": "Both company and location are required"}), 400

    # Use SerpAPI if key is available, otherwise Playwright fallback
    if SERP_API_KEY:
        raw = scrape_via_serpapi(company, location)
    else:
        raw = scrape_via_playwright(company, location)

    if raw.get("error") and not raw.get("name"):
        return jsonify({"error": raw["error"]}), 500

    return jsonify(post_process(raw))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")
