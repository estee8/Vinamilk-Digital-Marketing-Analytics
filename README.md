# Vinamilk-Digital-Marketing-Analytics

A multi-platform data analysis of Vinamilk's digital marketing performance, benchmarked against its two closest competitors, **TH true MILK** and **Nutifood**, across 6 digital channels.

## 📌 Overview

Vinamilk repositioned its brand identity in 2023 to modernize its image and expand internationally. This project evaluates how that shift has translated into actual digital marketing performance by measuring brand presence, content effectiveness, user engagement, and identifying strategic gaps across Vinamilk's digital ecosystem versus TH true MILK and Nutifood.

**Research questions:**
1. Where does Vinamilk currently stand across its digital platforms?
2. How does Vinamilk compare to TH true MILK and Nutifood?
3. Is there a gap between Vinamilk's brand messaging and users' real experience?

## 🗂️ Platforms & Data

| Channel | Tool used | Scope |
|---|---|---|
| Facebook | Apify | Posts, engagement, content format |
| TikTok | Apify | Videos, views, engagement, hashtags |
| YouTube | yt-dlp, youtube-transcript-api | Videos, Shorts vs. long-form, transcripts |
| LinkedIn | Python | Corporate posts, employer branding |
| App Store | Python | User reviews, ratings, sentiment |
| Online news | Python + Google News RSS | Press coverage, topics, source tiers |

Data covers Vinamilk, TH true MILK, and Nutifood, collected via an **ETLA pipeline** (Extract → Transform → Load → Analyze) built in Python on Google Colab.

## ⚙️ Methodology

- **Extract:** automated scraping (Apify, Python scripts, Google News RSS)
- **Transform:** cleaning, deduplication, missing-value handling, text normalization (Pandas)
- **Load:** structured CSV/Excel datasets per platform
- **Analyze:**
  - Descriptive & comparative KPI analysis (engagement rate, posting frequency, share of voice, etc.)
  - **Facebook:** Time-series engagement forecasting
  - **TikTok:** Performance clustering
  - **YouTube:** Regression on view count vs. video attributes
  - **LinkedIn:** Keyword/topic analysis
  - **App Store:** NLP sentiment analysis + assumed NPS
  - **Online news:** K-Means + TF-IDF topic clustering (Vietnamese NLP via `underthesea`)
  - **Video platforms:** Moving Average & Linear Trend (OLS) forecasting for TikTok/YouTube viewership

## 🔍 Key Findings

- Vinamilk **leads in brand presence**: highest post frequency on Facebook/LinkedIn, largest press coverage (364 articles / 95 sources), and Share of Voice around 60–61% since late 2023
- **Engagement quality lags scale**: median engagement is far below the mean on Facebook/TikTok, indicating performance driven by a few viral posts rather than consistent content quality
- **App Store experience is a major pain point**: 89.1% negative reviews, average rating 1.43/5, assumed NPS of **-81.7%**, driven mainly by loyalty-points and login issues
- **Losing ground on video platforms**: TH true MILK has overtaken Vinamilk on both TikTok (2.52B vs. 840M views) and YouTube since 2023, and forecast models show the gap widening on YouTube
- Five strategic **gaps** identified between Vinamilk's brand communication and actual user experience (loyalty program, one-way communication, ESG/CSR messaging, volume vs. quality content, video platform decline)

## 💡 Strategic Recommendations

1. Fix App Store loyalty-program and login issues before scaling related communication
2. Shift from one-way broadcasting to two-way engagement (interactive content formats, community-building)
3. Strengthen ESG/CSR communication to match the "Green Farm" sustainability positioning
4. Move from a volume-driven to a quality-driven content strategy
5. Reinvest in long-form/very-long TikTok content and rebuild a consistent YouTube content cadence to recover video-platform share
6. A 30-day action plan with weekly milestones and concrete KPI targets

## 🛠️ Tools & Libraries

- **Python** (Google Colab), **Pandas**, **NumPy**
- **scikit-learn** — regression, clustering, forecasting (OLS Linear Trend)
- **underthesea** — Vietnamese NLP / word segmentation
- **Seaborn / Matplotlib** — visualization & dashboards
- **Apify, yt-dlp, Google News RSS** — data collection
