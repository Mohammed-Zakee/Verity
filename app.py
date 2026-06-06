import re
import json
import time
import random
import asyncio
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from playwright.async_api import async_playwright

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────────────────────────────────────
# SENTIMENT ENGINE — keyword-based scoring (no API key needed)
# ─────────────────────────────────────────────────────────────────────────────
POSITIVE_WORDS = {
    "amazing", "excellent", "fantastic", "great", "love", "loved", "wonderful",
    "best", "perfect", "awesome", "outstanding", "superb", "brilliant", "friendly",
    "helpful", "clean", "fast", "quick", "fresh", "delicious", "beautiful",
    "recommend", "recommended", "impressive", "exceptional", "fabulous", "happy",
    "pleased", "satisfied", "good", "nice", "pleasant", "enjoy", "enjoyed",
    "polite", "professional", "efficient", "tasty", "cozy", "comfortable"
}

NEGATIVE_WORDS = {
    "terrible", "awful", "horrible", "worst", "bad", "poor", "disgusting",
    "rude", "slow", "dirty", "cold", "stale", "overpriced", "expensive",
    "disappointed", "disappointing", "unprofessional", "unhelpful", "never",
    "avoid", "waste", "disgusted", "unacceptable", "mediocre", "bland",
    "soggy", "broken", "filthy", "ignored", "wrong", "mistake", "charged",
    "complaint", "complained", "problem", "issue", "wait", "waiting", "hour",
    "hours", "long", "forever", "disgusting", "nasty", "gross", "sick"
}

THEME_KEYWORDS = {
    "Service":     ["service", "staff", "waiter", "waitress", "server", "manager", "employee",
                    "rude", "friendly", "helpful", "polite", "attentive", "ignored"],
    "Food/Product":["food", "meal", "dish", "taste", "flavor", "fresh", "stale", "delicious",
                    "bland", "cold", "hot", "cooked", "quality", "portion", "product"],
    "Wait Time":   ["wait", "waiting", "slow", "fast", "quick", "minutes", "hours", "long",
                    "forever", "delay", "delayed", "rush"],
    "Cleanliness": ["clean", "dirty", "filthy", "hygiene", "sanitary", "bathroom", "restroom",
                    "smell", "smelly", "tidy", "neat", "messy"],
    "Value":       ["price", "expensive", "cheap", "overpriced", "worth", "value", "costly",
                    "affordable", "money", "charge", "charged", "fee", "bill"],
    "Ambience":    ["atmosphere", "ambience", "vibe", "noise", "loud", "quiet", "cozy",
                    "comfortable", "crowded", "parking", "location", "decor", "music"]
}

def analyze_sentiment(text: str) -> dict:
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    pos = sum(1 for w in words if w in POSITIVE_WORDS)
    neg = sum(1 for w in words if w in NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        score = 0.5
        label = "Neutral"
    else:
        score = pos / total
        if score >= 0.65:
            label = "Positive"
        elif score <= 0.35:
            label = "Negative"
        else:
            label = "Mixed"
    return {"score": round(score, 3), "label": label, "positive": pos, "negative": neg}

def extract_themes(reviews: list) -> dict:
    theme_counts = {t: {"mentions": 0, "positive": 0, "negative": 0} for t in THEME_KEYWORDS}
    for review in reviews:
        text = review.get("text", "").lower()
        words = set(re.findall(r'\b[a-zA-Z]+\b', text))
        sentiment = review.get("sentiment", {})
        for theme, keywords in THEME_KEYWORDS.items():
            if any(k in words for k in keywords):
                theme_counts[theme]["mentions"] += 1
                if sentiment.get("label") == "Positive":
                    theme_counts[theme]["positive"] += 1
                elif sentiment.get("label") == "Negative":
                    theme_counts[theme]["negative"] += 1
    return theme_counts

def detect_red_flags(reviews: list) -> list:
    complaint_freq = {}
    for review in reviews:
        if review.get("rating", 5) <= 2:
            words = re.findall(r'\b[a-zA-Z]{4,}\b', review.get("text", "").lower())
            for w in words:
                if w in NEGATIVE_WORDS:
                    complaint_freq[w] = complaint_freq.get(w, 0) + 1
    sorted_flags = sorted(complaint_freq.items(), key=lambda x: x[1], reverse=True)
    return [{"word": w, "count": c} for w, c in sorted_flags[:8]]

def extract_word_frequency(reviews: list) -> list:
    STOPWORDS = {"the","a","an","and","or","but","in","on","at","to","for","of","is",
                 "was","it","i","we","my","me","they","their","this","that","with",
                 "have","had","not","be","are","were","our","us","he","she","his","her",
                 "its","by","as","if","so","do","did","from","up","out","about","been",
                 "can","will","would","just","there","then","than","your","you","very",
                 "also","get","got","all","has","her","him","like","one","more","when",
                 "what","which","who","how","no","yes","well","over","too","only","even"}
    freq = {}
    for review in reviews:
        words = re.findall(r'\b[a-zA-Z]{4,}\b', review.get("text", "").lower())
        for w in words:
            if w not in STOPWORDS:
                freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [{"word": w, "count": c} for w, c in sorted_words[:50]]

def build_timeline(reviews: list) -> list:
    monthly = {}
    for review in reviews:
        date_str = review.get("date", "")
        if not date_str:
            continue
        # Parse relative dates like "2 months ago", "a year ago", "3 weeks ago"
        now = datetime.now()
        try:
            if "month" in date_str:
                n = 1 if date_str.startswith("a") else int(re.search(r'\d+', date_str).group())
                month = now.month - n
                year = now.year
                while month <= 0:
                    month += 12
                    year -= 1
                key = f"{year}-{month:02d}"
            elif "year" in date_str:
                n = 1 if date_str.startswith("a") else int(re.search(r'\d+', date_str).group())
                key = f"{now.year - n}-{now.month:02d}"
            elif "week" in date_str:
                key = f"{now.year}-{now.month:02d}"
            elif "day" in date_str or "hour" in date_str or "minute" in date_str:
                key = f"{now.year}-{now.month:02d}"
            else:
                key = f"{now.year}-{now.month:02d}"
        except Exception:
            key = f"{now.year}-{now.month:02d}"

        r = review.get("rating")
        if r:
            if key not in monthly:
                monthly[key] = {"ratings": [], "count": 0}
            monthly[key]["ratings"].append(r)
            monthly[key]["count"] += 1

    timeline = []
    for k, v in sorted(monthly.items()):
        avg = sum(v["ratings"]) / len(v["ratings"])
        timeline.append({"month": k, "avg_rating": round(avg, 2), "count": v["count"]})
    return timeline


# ─────────────────────────────────────────────────────────────────────────────
# PLAYWRIGHT SCRAPER
# ─────────────────────────────────────────────────────────────────────────────
async def scrape_google_maps(company: str, location: str) -> dict:
    query = f"{company} {location}"
    result = {
        "company": company,
        "location": location,
        "query": query,
        "scraped_at": datetime.now().isoformat(),
        "name": None,
        "address": None,
        "phone": None,
        "website": None,
        "category": None,
        "rating": None,
        "review_count": None,
        "hours": [],
        "photos": [],
        "coordinates": None,
        "reviews": [],
        "error": None
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
            locale="en-US"
        )
        page = await context.new_page()

        try:
            search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            # If results list appears, click the first one
            first_result = page.locator('a[href*="/maps/place/"]').first
            if await first_result.count() > 0:
                await first_result.click()
                await page.wait_for_timeout(3000)

            # ── Basic Info ──
            try:
                result["name"] = await page.locator('h1.DUwDvf').first.inner_text(timeout=5000)
            except Exception:
                try:
                    result["name"] = await page.locator('[data-item-id="authority"] .fontHeadlineLarge').first.inner_text(timeout=3000)
                except Exception:
                    result["name"] = company

            try:
                result["category"] = await page.locator('button[jsaction*="category"]').first.inner_text(timeout=3000)
            except Exception:
                try:
                    result["category"] = await page.locator('.DkEaL').first.inner_text(timeout=3000)
                except Exception:
                    pass

            # Rating
            try:
                rating_text = await page.locator('div.F7nice span[aria-hidden="true"]').first.inner_text(timeout=5000)
                result["rating"] = float(rating_text.strip())
            except Exception:
                try:
                    rating_text = await page.locator('span.ceNzKf').get_attribute("aria-label", timeout=3000)
                    m = re.search(r'([\d.]+)', rating_text or "")
                    if m:
                        result["rating"] = float(m.group(1))
                except Exception:
                    pass

            # Review count
            try:
                count_text = await page.locator('div.F7nice span[aria-label*="review"]').first.inner_text(timeout=3000)
                m = re.search(r'([\d,]+)', count_text)
                if m:
                    result["review_count"] = int(m.group(1).replace(",", ""))
            except Exception:
                try:
                    count_el = await page.locator('button[jsaction*="reviewChart"] span').first.inner_text(timeout=3000)
                    m = re.search(r'([\d,]+)', count_el)
                    if m:
                        result["review_count"] = int(m.group(1).replace(",", ""))
                except Exception:
                    pass

            # Address
            try:
                addr_el = page.locator('[data-item-id="address"]')
                if await addr_el.count() > 0:
                    result["address"] = await addr_el.first.inner_text(timeout=3000)
            except Exception:
                pass

            # Phone
            try:
                phone_el = page.locator('[data-item-id*="phone"]')
                if await phone_el.count() > 0:
                    result["phone"] = await phone_el.first.inner_text(timeout=3000)
            except Exception:
                pass

            # Website
            try:
                web_el = page.locator('[data-item-id="authority"]')
                if await web_el.count() > 0:
                    result["website"] = await web_el.first.inner_text(timeout=3000)
            except Exception:
                pass

            # Opening Hours
            try:
                await page.locator('[data-item-id="oh"]').first.click(timeout=3000)
                await page.wait_for_timeout(1000)
                hours_rows = await page.locator('table.eK4R0e tr').all()
                for row in hours_rows:
                    try:
                        day = await row.locator('td').first.inner_text(timeout=1000)
                        hours = await row.locator('td').nth(1).inner_text(timeout=1000)
                        result["hours"].append({"day": day.strip(), "hours": hours.strip()})
                    except Exception:
                        pass
            except Exception:
                pass

            # ── Reviews ──
            try:
                reviews_btn = page.locator('button[aria-label*="review"]')
                if await reviews_btn.count() == 0:
                    reviews_btn = page.locator('div[role="tab"]:has-text("Reviews")')
                if await reviews_btn.count() > 0:
                    await reviews_btn.first.click()
                    await page.wait_for_timeout(2000)
            except Exception:
                pass

            # Sort by newest
            try:
                sort_btn = page.locator('button[aria-label*="Sort"]')
                if await sort_btn.count() > 0:
                    await sort_btn.first.click()
                    await page.wait_for_timeout(1000)
                    newest = page.locator('div[role="menuitemradio"]:has-text("Newest")')
                    if await newest.count() > 0:
                        await newest.first.click()
                        await page.wait_for_timeout(2000)
            except Exception:
                pass

            # Scroll to load reviews
            review_container = page.locator('div[role="main"]')
            for _ in range(8):
                try:
                    await review_container.evaluate("el => el.scrollTop += 1200")
                    await page.wait_for_timeout(800)
                except Exception:
                    break

            # Extract reviews
            review_elements = await page.locator('div[data-review-id]').all()
            for el in review_elements[:50]:
                try:
                    author = await el.locator('.d4r55').first.inner_text(timeout=2000)
                    try:
                        date = await el.locator('.rsqaWe').first.inner_text(timeout=2000)
                    except Exception:
                        date = ""
                    try:
                        rating_attr = await el.locator('span[role="img"]').first.get_attribute("aria-label", timeout=2000)
                        r_match = re.search(r'(\d)', rating_attr or "")
                        rating_val = int(r_match.group(1)) if r_match else None
                    except Exception:
                        rating_val = None
                    try:
                        # Expand review if truncated
                        more_btn = el.locator('button.w8nwRe')
                        if await more_btn.count() > 0:
                            await more_btn.click()
                            await page.wait_for_timeout(300)
                        text = await el.locator('.wiI7pd').first.inner_text(timeout=2000)
                    except Exception:
                        text = ""

                    sentiment = analyze_sentiment(text)
                    result["reviews"].append({
                        "author": author.strip(),
                        "date": date.strip(),
                        "rating": rating_val,
                        "text": text.strip(),
                        "sentiment": sentiment
                    })
                except Exception:
                    continue

        except Exception as e:
            result["error"] = str(e)
        finally:
            await browser.close()

    return result


def post_process(data: dict) -> dict:
    reviews = data.get("reviews", [])
    if reviews:
        total_pos = sum(r["sentiment"]["positive"] for r in reviews)
        total_neg = sum(r["sentiment"]["negative"] for r in reviews)
        total = total_pos + total_neg
        data["sentiment_summary"] = {
            "positive_pct": round(total_pos / total * 100, 1) if total else 50,
            "negative_pct": round(total_neg / total * 100, 1) if total else 50,
            "neutral_pct": 0,
            "labels": {
                "positive": sum(1 for r in reviews if r["sentiment"]["label"] == "Positive"),
                "negative": sum(1 for r in reviews if r["sentiment"]["label"] == "Negative"),
                "mixed":    sum(1 for r in reviews if r["sentiment"]["label"] == "Mixed"),
                "neutral":  sum(1 for r in reviews if r["sentiment"]["label"] == "Neutral"),
            }
        }
    else:
        data["sentiment_summary"] = {"positive_pct": 0, "negative_pct": 0, "neutral_pct": 100,
                                     "labels": {"positive": 0, "negative": 0, "mixed": 0, "neutral": 0}}

    data["themes"]     = extract_themes(reviews)
    data["red_flags"]  = detect_red_flags(reviews)
    data["word_freq"]  = extract_word_frequency(reviews)
    data["timeline"]   = build_timeline(reviews)
    return data


# ─────────────────────────────────────────────────────────────────────────────
# FLASK ROUTES
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/scrape", methods=["POST"])
def scrape():
    body = request.get_json()
    company  = (body.get("company") or "").strip()
    location = (body.get("location") or "").strip()

    if not company or not location:
        return jsonify({"error": "Company name and location are required"}), 400

    try:
        raw = asyncio.run(scrape_google_maps(company, location))
        processed = post_process(raw)
        return jsonify(processed)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
