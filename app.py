"""
Verity Backend — 100% Self-Built
=================================
- Scrapes Google Maps directly via Playwright (headless Chromium)
- Sentiment analysis via our own keyword NLP engine
- No SerpAPI. No Hugging Face. No third-party data services.
- Just a real browser, hitting real URLs, analyzing data ourselves.
"""

import os
import re
import json
import asyncio
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

app = Flask(__name__)
CORS(app, origins=["*"], methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type"])

# ─────────────────────────────────────────────────────────────────────────────
# OUR OWN SENTIMENT ENGINE — Zero external dependencies
# ─────────────────────────────────────────────────────────────────────────────

POSITIVE_WORDS = {
    "amazing", "excellent", "fantastic", "great", "love", "loved", "wonderful",
    "best", "perfect", "awesome", "outstanding", "superb", "brilliant", "friendly",
    "helpful", "clean", "fast", "quick", "fresh", "delicious", "beautiful",
    "recommend", "recommended", "impressive", "exceptional", "fabulous", "happy",
    "pleased", "satisfied", "good", "nice", "pleasant", "enjoy", "enjoyed",
    "polite", "professional", "efficient", "tasty", "cozy", "comfortable",
    "stunning", "incredible", "spotless", "attentive", "generous", "welcoming",
    "prompt", "courteous", "spectacular", "divine", "flawless", "reasonable",
    "affordable", "worth", "quality", "fresh", "warm", "caring", "genuine"
}

NEGATIVE_WORDS = {
    "terrible", "awful", "horrible", "worst", "bad", "poor", "disgusting",
    "rude", "slow", "dirty", "cold", "stale", "overpriced", "expensive",
    "disappointed", "disappointing", "unprofessional", "unhelpful", "never",
    "avoid", "waste", "disgusted", "unacceptable", "mediocre", "bland",
    "soggy", "broken", "filthy", "ignored", "wrong", "mistake", "charged",
    "complaint", "complained", "problem", "issue", "wait", "waiting",
    "long", "forever", "nasty", "gross", "sick", "toxic", "rip", "scam",
    "fraudulent", "lied", "incompetent", "careless", "lazy", "sloppy",
    "disgusting", "pathetic", "unclean", "overcrowded", "noisy", "rotten"
}

NEGATION_WORDS = {"not", "never", "no", "nothing", "nowhere", "neither",
                  "barely", "hardly", "scarcely", "without", "won't", "don't",
                  "didn't", "doesn't", "wasn't", "isn't", "aren't", "wouldn't"}

THEME_KEYWORDS = {
    "Service":      ["service", "staff", "waiter", "waitress", "server", "manager",
                     "employee", "rude", "friendly", "helpful", "polite", "attentive",
                     "ignored", "receptionist", "cashier", "host", "hostess", "crew"],
    "Food/Product": ["food", "meal", "dish", "taste", "flavor", "fresh", "stale",
                     "delicious", "bland", "cold", "hot", "cooked", "quality", "portion",
                     "product", "drink", "coffee", "menu", "dessert", "appetizer", "pizza",
                     "burger", "sushi", "pasta", "soup", "salad", "breakfast", "lunch", "dinner"],
    "Wait Time":    ["wait", "waiting", "slow", "fast", "quick", "minutes", "hours",
                     "long", "forever", "delay", "delayed", "rush", "queue", "line"],
    "Cleanliness":  ["clean", "dirty", "filthy", "hygiene", "sanitary", "bathroom",
                     "restroom", "smell", "smelly", "tidy", "neat", "messy", "dusty",
                     "grimy", "spotless", "stained", "cockroach", "pest"],
    "Value":        ["price", "expensive", "cheap", "overpriced", "worth", "value",
                     "costly", "affordable", "money", "charge", "charged", "fee",
                     "bill", "cost", "markup", "discount", "deal", "budget"],
    "Ambience":     ["atmosphere", "ambience", "vibe", "noise", "loud", "quiet",
                     "cozy", "comfortable", "crowded", "parking", "location", "decor",
                     "music", "lighting", "seating", "view", "aesthetic", "aesthetic"]
}


def analyze_sentiment(text: str) -> dict:
    """
    Our own sentiment analyzer.
    - Tokenizes text
    - Handles negation (e.g. 'not good' flips the polarity)
    - Returns label, score, word counts
    """
    tokens = re.findall(r"\b[a-zA-Z']+\b", text.lower())
    pos = 0
    neg = 0
    negated = False

    for i, token in enumerate(tokens):
        # Check if previous word was a negation
        if i > 0 and tokens[i - 1] in NEGATION_WORDS:
            negated = True
        else:
            negated = False

        if token in POSITIVE_WORDS:
            if negated:
                neg += 1   # "not good" → negative signal
            else:
                pos += 1
        elif token in NEGATIVE_WORDS:
            if negated:
                pos += 1   # "not bad" → positive signal
            else:
                neg += 1

    total = pos + neg
    if total == 0:
        return {"score": 0.5, "label": "Neutral", "positive": 0, "negative": 0}

    score = pos / total
    if score >= 0.65:
        label = "Positive"
    elif score <= 0.35:
        label = "Negative"
    else:
        label = "Mixed"

    return {"score": round(score, 3), "label": label, "positive": pos, "negative": neg}


def extract_themes(reviews: list) -> dict:
    counts = {t: {"mentions": 0, "positive": 0, "negative": 0} for t in THEME_KEYWORDS}
    for review in reviews:
        text  = review.get("text", "").lower()
        words = set(re.findall(r"\b[a-zA-Z]+\b", text))
        label = review.get("sentiment", {}).get("label", "")
        for theme, keywords in THEME_KEYWORDS.items():
            if any(k in words for k in keywords):
                counts[theme]["mentions"] += 1
                if label == "Positive":
                    counts[theme]["positive"] += 1
                elif label == "Negative":
                    counts[theme]["negative"] += 1
    return counts


def detect_red_flags(reviews: list) -> list:
    freq = {}
    for review in reviews:
        if review.get("rating") and review["rating"] <= 2:
            words = re.findall(r"\b[a-zA-Z]{4,}\b", review.get("text", "").lower())
            for w in words:
                if w in NEGATIVE_WORDS:
                    freq[w] = freq.get(w, 0) + 1
    return [{"word": w, "count": c}
            for w, c in sorted(freq.items(), key=lambda x: -x[1])[:8]]


def extract_word_frequency(reviews: list) -> list:
    STOP = {
        "the","a","an","and","or","but","in","on","at","to","for","of","is","was",
        "it","i","we","my","me","they","this","that","with","have","had","not","be",
        "are","were","our","us","he","she","his","her","its","by","as","if","so",
        "do","did","from","up","out","about","been","can","will","would","just",
        "there","then","than","your","you","very","also","get","got","all","has",
        "like","one","more","when","what","which","who","how","no","yes","well",
        "over","too","only","even","some","time","really","went","here","their",
        "place","back","came","come","into","been","every","other","again","could",
        "should","after","before","still","always","never","each","much","many",
        "food","great","good","nice","really","always","went","place","back","very"
    }
    freq = {}
    for review in reviews:
        for w in re.findall(r"\b[a-zA-Z]{4,}\b", review.get("text", "").lower()):
            if w not in STOP:
                freq[w] = freq.get(w, 0) + 1
    return [{"word": w, "count": c}
            for w, c in sorted(freq.items(), key=lambda x: -x[1])[:50]]


def build_timeline(reviews: list) -> list:
    now     = datetime.now()
    monthly = {}
    for review in reviews:
        date_str = review.get("date", "")
        try:
            if "month" in date_str:
                n = 1 if date_str.startswith("a") else int(re.search(r"\d+", date_str).group())
                m, y = now.month - n, now.year
                while m <= 0:
                    m += 12; y -= 1
                key = f"{y}-{m:02d}"
            elif "year" in date_str:
                n = 1 if date_str.startswith("a") else int(re.search(r"\d+", date_str).group())
                key = f"{now.year - n}-{now.month:02d}"
            elif "week" in date_str or "day" in date_str or "hour" in date_str:
                key = f"{now.year}-{now.month:02d}"
            else:
                key = f"{now.year}-{now.month:02d}"
        except Exception:
            key = f"{now.year}-{now.month:02d}"
        r = review.get("rating")
        if r:
            monthly.setdefault(key, []).append(r)
    return [{"month": k, "avg_rating": round(sum(v) / len(v), 2), "count": len(v)}
            for k, v in sorted(monthly.items())]


# ─────────────────────────────────────────────────────────────────────────────
# PLAYWRIGHT SCRAPER — We drive the browser ourselves
# ─────────────────────────────────────────────────────────────────────────────

async def scrape_google_maps(company: str, location: str) -> dict:
    """
    Drives a real Chromium browser to Google Maps.
    No external scraping API — we do it ourselves.
    Uses a robust 2-step bypass to avoid the "limited view" restriction on signed-out users.
    """
    result = {
        "company":      company,
        "location":     location,
        "scraped_at":   datetime.now().isoformat(),
        "name":         None,
        "address":      None,
        "phone":        None,
        "website":      None,
        "category":     None,
        "rating":       None,
        "review_count": None,
        "hours":        [],
        "photos":       [],
        "reviews":      [],
        "error":        None,
    }

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        page = await context.new_page()

        try:
            # ── Step 1: Initial search to extract basic info & discover category ──
            query      = f"{company} {location}".replace(" ", "+")
            search_url = f"https://www.google.com/maps/search/{query}"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=35000)
            await page.wait_for_timeout(2500)

            # Click first result if we're on the results list
            first = page.locator('a[href*="/maps/place/"]').first
            if await first.count() > 0:
                await first.click()
                await page.wait_for_timeout(3000)

            # Extract name
            for selector in ["h1.DUwDvf", "h1.fontHeadlineLarge", "[data-attrid='title']"]:
                try:
                    el = page.locator(selector).first
                    if await el.count() > 0:
                        result["name"] = (await el.inner_text(timeout=4000)).strip()
                        break
                except Exception:
                    pass
            result["name"] = result["name"] or company

            # Extract category
            for selector in ["button[jsaction*='category']", ".DkEaL", ".fontBodyMedium.dmRXdf"]:
                try:
                    el = page.locator(selector).first
                    if await el.count() > 0:
                        result["category"] = (await el.inner_text(timeout=3000)).strip()
                        break
                except Exception:
                    pass

            # Extract rating
            try:
                rt = await page.locator("div.F7nice span[aria-hidden='true']").first.inner_text(timeout=4000)
                result["rating"] = float(rt.strip().replace(",", "."))
            except Exception:
                try:
                    attr = await page.locator("span.ceNzKf").get_attribute("aria-label", timeout=3000)
                    m = re.search(r"([\d.]+)", attr or "")
                    if m:
                        result["rating"] = float(m.group(1))
                except Exception:
                    pass

            # Extract review count
            try:
                ct = await page.locator("div.F7nice span[aria-label*='review']").first.inner_text(timeout=3000)
                m  = re.search(r"([\d,]+)", ct)
                if m:
                    result["review_count"] = int(m.group(1).replace(",", ""))
            except Exception:
                try:
                    ct = await page.locator("button[jsaction*='reviewChart'] span").first.inner_text(timeout=3000)
                    m  = re.search(r"([\d,]+)", ct)
                    if m:
                        result["review_count"] = int(m.group(1).replace(",", ""))
                except Exception:
                    pass

            # Extract address
            try:
                el = page.locator("[data-item-id='address']")
                if await el.count() > 0:
                    result["address"] = (await el.first.inner_text(timeout=3000)).strip()
            except Exception:
                pass

            # Extract phone
            try:
                el = page.locator("[data-item-id*='phone']")
                if await el.count() > 0:
                    result["phone"] = (await el.first.inner_text(timeout=3000)).strip()
            except Exception:
                pass

            # Extract website
            try:
                el = page.locator("[data-item-id='authority']")
                if await el.count() > 0:
                    result["website"] = (await el.first.inner_text(timeout=3000)).strip()
            except Exception:
                pass

            # Extract opening hours
            try:
                hours_btn = page.locator("[data-item-id='oh']").first
                if await hours_btn.count() > 0:
                    await hours_btn.click(timeout=3000)
                    await page.wait_for_timeout(1000)
                rows = await page.locator("table.eK4R0e tr").all()
                for row in rows:
                    try:
                        cells = await row.locator("td").all()
                        if len(cells) >= 2:
                            day   = (await cells[0].inner_text(timeout=1000)).strip()
                            hours = (await cells[1].inner_text(timeout=1000)).strip()
                            result["hours"].append({"day": day, "hours": hours})
                    except Exception:
                        pass
            except Exception:
                pass

            # ── Step 2: Navigate via Category list search to bypass limited view ──
            # This forces Google Maps to load the business within the search list context,
            # which preserves the full reviews tab for signed-out users.
            list_category = result["category"] or "business"
            list_query = f"{list_category} near {location}".replace(" ", "+")
            list_url = f"https://www.google.com/maps/search/{list_query}"
            
            print(f"Bypassing limited view. Searching list: {list_url}")
            await page.goto(list_url, wait_until="domcontentloaded", timeout=35000)
            await page.wait_for_timeout(3500)
            
            # Find the business link in the search results list
            links = await page.locator('a[href*="/maps/place/"]').all()
            target_link = None
            target_name_lower = result["name"].lower()
            
            for link in links:
                try:
                    aria = await link.get_attribute("aria-label", timeout=1000) or ""
                    text = await link.inner_text(timeout=1000) or ""
                    if target_name_lower in aria.lower() or target_name_lower in text.lower():
                        target_link = link
                        break
                except Exception:
                    pass
            
            if target_link:
                print(f"Found match '{result['name']}' in list. Clicking to load full view...")
                await target_link.click()
                await page.wait_for_timeout(4000)
            else:
                print(f"Target '{result['name']}' not found in search list. Falling back to first result...")
                if len(links) > 0:
                    await links[0].click()
                    await page.wait_for_timeout(4000)
                else:
                    # If we couldn't find a list, navigate back to original search and hope for the best
                    print("List search empty. Returning to direct url...")
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=35000)
                    await page.wait_for_timeout(3000)

            # ── Step 3: Navigate to Reviews tab ──
            try:
                for sel in [
                    "button[aria-label*='Reviews']",
                    "button[aria-label*='reviews']",
                    "button[aria-label*='review']",
                    "div[role='tab']:has-text('Reviews')",
                ]:
                    btn = page.locator(sel)
                    if await btn.count() > 0:
                        await btn.first.click()
                        await page.wait_for_timeout(2000)
                        break
            except Exception:
                pass

            # Sort by Newest
            try:
                sort_btn = page.locator("button[aria-label*='Sort']")
                if await sort_btn.count() > 0:
                    await sort_btn.first.click()
                    await page.wait_for_timeout(800)
                    newest = page.locator("div[role='menuitemradio']:has-text('Newest')")
                    if await newest.count() > 0:
                        await newest.first.click()
                        await page.wait_for_timeout(2000)
            except Exception:
                pass

            # Scroll to load more reviews
            panel = page.locator("div[role='main']")
            for _ in range(10):
                try:
                    await panel.evaluate("el => el.scrollTop += 1400")
                    await page.wait_for_timeout(700)
                except Exception:
                    break

            # ── Step 4: Extract Reviews ──
            review_els = await page.locator("div[data-review-id]").all()
            for el in review_els[:50]:
                try:
                    # Author
                    author = ""
                    for sel in [".d4r55", ".DUwDvf"]:
                        try:
                            a = el.locator(sel).first
                            if await a.count() > 0:
                                author = (await a.inner_text(timeout=2000)).strip()
                                break
                        except Exception:
                            pass

                    # Date
                    date = ""
                    for sel in [".rsqaWe", ".xRkPPb"]:
                        try:
                            d = el.locator(sel).first
                            if await d.count() > 0:
                                date = (await d.inner_text(timeout=2000)).strip()
                                break
                        except Exception:
                            pass

                    # Star rating
                    rating_val = None
                    try:
                        aria = await el.locator("span[role='img']").first.get_attribute("aria-label", timeout=2000)
                        m = re.search(r"(\d)", aria or "")
                        if m:
                            rating_val = int(m.group(1))
                    except Exception:
                        pass

                    # Review text — expand truncated first
                    text = ""
                    try:
                        more = el.locator("button.w8nwRe")
                        if await more.count() > 0:
                            await more.click()
                            await page.wait_for_timeout(250)
                    except Exception:
                        pass
                    for sel in [".wiI7pd", ".MyEned", "span[data-expandable-section]"]:
                        try:
                            t = el.locator(sel).first
                            if await t.count() > 0:
                                text = (await t.inner_text(timeout=2000)).strip()
                                if text:
                                    break
                        except Exception:
                            pass

                    # Extract review photos
                    photos = []
                    try:
                        buttons = await el.locator("button").all()
                        for btn_el in buttons:
                            style_attr = await btn_el.get_attribute("style") or ""
                            aria_attr = await btn_el.get_attribute("aria-label") or ""
                            if "background-image" in style_attr and "review" in aria_attr.lower():
                                m = re.search(r'url\([\'"]?([^\'"]+?)[\'"]?\)', style_attr)
                                if m:
                                    photos.append(m.group(1))
                    except Exception:
                        pass

                    sentiment = analyze_sentiment(text)
                    result["reviews"].append({
                        "author":    author or "Anonymous",
                        "date":      date,
                        "rating":    rating_val,
                        "text":      text,
                        "sentiment": sentiment,
                        "photos":    photos,
                    })
                except Exception:
                    continue

        except PWTimeout:
            result["error"] = "Timed out loading Google Maps. Try again."
        except Exception as e:
            result["error"] = str(e)
        finally:
            await browser.close()

    return result


def post_process(data: dict) -> dict:
    reviews = data.get("reviews", [])
    labels  = {"Positive": 0, "Negative": 0, "Mixed": 0, "Neutral": 0}
    for r in reviews:
        l = r.get("sentiment", {}).get("label", "Neutral")
        labels[l] = labels.get(l, 0) + 1
    total = sum(labels.values()) or 1

    data["sentiment_summary"] = {
        "positive_pct": round(labels["Positive"] / total * 100, 1),
        "negative_pct": round(labels["Negative"] / total * 100, 1),
        "neutral_pct":  round((labels["Mixed"] + labels["Neutral"]) / total * 100, 1),
        "labels": labels,
    }
    data["themes"]    = extract_themes(reviews)
    data["red_flags"] = detect_red_flags(reviews)
    data["word_freq"] = extract_word_frequency(reviews)
    data["timeline"]  = build_timeline(reviews)
    return data


# ─────────────────────────────────────────────────────────────────────────────
# FLASK ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status":  "ok",
        "engine":  "playwright + self-built NLP",
        "third_party_apis": "none",
        "version": "3.0.0",
    })


@app.route("/api/scrape", methods=["POST", "OPTIONS"])
def scrape():
    if request.method == "OPTIONS":
        return jsonify({"ok": True})

    body     = request.get_json(silent=True) or {}
    company  = (body.get("company")  or "").strip()
    location = (body.get("location") or "").strip()

    if not company or not location:
        return jsonify({"error": "Both 'company' and 'location' are required."}), 400

    try:
        raw       = asyncio.run(scrape_google_maps(company, location))
        processed = post_process(raw)
    except RuntimeError as e:
        # asyncio.run() inside an already-running loop (gunicorn worker edge case)
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, scrape_google_maps(company, location))
            raw    = future.result(timeout=120)
        processed = post_process(raw)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Check for scraper error when no reviews were successfully retrieved
    if processed.get("error") and not processed.get("reviews"):
        return jsonify({"error": processed["error"]}), 500

    # Verify if we actually found and scraped any real business details
    has_details = (
        processed.get("address") or 
        processed.get("phone") or 
        processed.get("website") or 
        processed.get("category") or 
        processed.get("rating") is not None or 
        processed.get("reviews")
    )
    if not has_details:
        err_msg = processed.get("error") or f"Could not find or scrape business '{company}' in '{location}'."
        return jsonify({"error": err_msg}), 404

    return jsonify(processed)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
