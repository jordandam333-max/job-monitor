# Lookout — hiring signal tracker

Watches other companies' career pages, checks for new job postings on a schedule,
and shows what's new on a simple dashboard page.

## How it works

1. `scripts/scrape.py` fetches each site listed in `scripts/sites.json`, pulls out
   job titles/links using CSS selectors you configure per site, and compares them
   against what it saw last time (`data/state.json`).
2. New jobs get flagged and everything is written to `docs/data.json`.
3. `docs/index.html` is a small dashboard that reads `docs/data.json` and displays
   it — new roles are highlighted.
4. `.github/workflows/monitor.yml` runs step 1–2 automatically every 30 minutes
   using GitHub Actions, and commits the updated data back to the repo.
5. GitHub Pages serves the `docs/` folder as a live website, so the dashboard is
   always up to date — you just open the page whenever you want to check.

## Setup

1. **Create a GitHub repo** and push these files to it.

2. **Turn on GitHub Pages**
   - Repo → Settings → Pages
   - Source: "Deploy from a branch"
   - Branch: `main`, folder: `/docs`
   - Save. GitHub will give you a URL like `https://yourname.github.io/repo-name/` —
     that's your dashboard link. Bookmark it.

3. **Configure the sites to track** — edit `scripts/sites.json`. For each site
   you want to monitor, you need:
   - `url` — the careers page to check
   - `job_selector` — a CSS selector matching each job listing on the page
   - `title_selector` — CSS selector (relative to each job listing) for the job title
   - `link_selector` — CSS selector (relative to each job listing) for the link element
   - `base_url` — the site's root domain, used to resolve relative links

   **How to find these selectors:** open the careers page in Chrome, right-click
   a job listing → Inspect, and look at the surrounding HTML to find a repeated
   class name or tag that wraps each listing. That becomes `job_selector`.

   If the company uses a known ATS, their page is usually more predictable:
   - **Greenhouse** (`boards.greenhouse.io/...`): `job_selector: "div.opening"`
   - **Lever** (`jobs.lever.co/...`): `job_selector: "div.posting"`

4. **Enable Actions permissions** — Repo → Settings → Actions → General →
   Workflow permissions → "Read and write permissions". This lets the workflow
   commit updated data back to the repo.

5. **Run it once manually** to confirm it works — Repo → Actions tab →
   "Job Monitor" → Run workflow. After it finishes, refresh your dashboard URL.

After that, it runs on its own every 30 minutes (change the `cron` line in
`.github/workflows/monitor.yml` to run more or less often — minimum is every
5 minutes on GitHub's free tier).

## Running locally (optional, for testing selectors)

```bash
pip install requests beautifulsoup4
python3 scripts/scrape.py
```

This writes `docs/data.json`, which you can open in a browser locally alongside
`docs/index.html` (serve the `docs/` folder with `python3 -m http.server` rather
than opening the file directly, so the `fetch('data.json')` call works).

## Notes and limits

- **Social media monitoring isn't included here.** LinkedIn/Instagram/X don't
  offer a free way to reliably watch an arbitrary company's posts — that would
  need a paid social-listening API or a much more fragile scraper. This tool
  covers career-page monitoring, which is the more reliable win.
- **Check each site's terms of service / robots.txt** before scraping it.
  Some explicitly disallow automated access.
- If a site redesigns its careers page, its `job_selector` will likely need
  updating — that's the main maintenance cost of this approach.
