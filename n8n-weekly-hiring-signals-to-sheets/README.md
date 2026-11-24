# Weekly hiring signals to Google Sheets (n8n)

Every Monday this reads the roles your watchlist companies published in the last 7 days, using the Apify actor [career-site-jobs](https://apify.com/improved_gravity_qb7/greenhouse-lever-ashby-personio-jobs-scraper). It writes them to Google Sheets: one tab of jobs and one tab of per-company signals. It works with Greenhouse, Lever, Ashby, Workable, Personio and Recruitee boards. Typical uses are tracking competitors' hiring, recruiter and sales lead lists, and investor watchlists.

Disclosure: built and sold by the actor's owner. The actor is paid ($0.003 per job returned on Apify's Free and Starter plans, less on higher plans), and that money goes to the person who wrote this template.

File: `workflow.json`. In n8n, open a new workflow, then paste the file contents or use *Import from File*.

## How it works

`Every Monday at 08:00` (Schedule Trigger) → `Watchlist and filters` (Set) → `Read new roles` (Apify node, *Actors → Run an Actor and get dataset*, actor `go8YB1qv3eEb4IU4J` = improved_gravity_qb7/greenhouse-lever-ashby-personio-jobs-scraper). The result then splits into two branches:

- `Job row columns` (Set) → `Jobs tab: add or update by id` (Google Sheets, *Append or Update Row*, matched on `id`). One row per role, so a rerun updates rows instead of duplicating them. `last_seen` is the date of the latest run that returned the role.
- `Summarise per company` (Code) → `Signals tab: add rows` (Google Sheets, *Append Row*). Each run adds one row per company with: `week`, `company`, `board`, `window_days`, `roles_posted`, `top_departments`, `top_countries`, `remote_roles`, `roles_with_salary` and `example_titles`.

This template does not use `newJobsOnly` and needs no Apify task. The 7-day window (`postedWithinDays`) is what limits each run to recent roles, and the actor stores no history between runs.

## Prerequisites

- n8n with the Apify community node `@apify/n8n-nodes-apify` installed. Self-hosted: *Settings → Community Nodes → Install*. n8n Cloud: search "Apify" in the nodes panel; the instance owner must first allow verified community nodes. The workflow was checked against node version 0.9.1.
- An Apify account and API token (Apify Console → Settings → API & Integrations).
- A Google account for the Sheets OAuth2 credential.

## Setup (about 5 minutes)

1. **Watchlist.** In `Watchlist and filters`, edit `companies`. Each entry can be a career page URL, `system:board` (`greenhouse:stripe`) or a bare board name, which the actor tries on each system. Optional fields: `keyword` (every word must be in the title), `country` (`DE` or `Germany`), `postedWithinDays` (default 7, which matches the weekly schedule) and `maxJobs` (default 500).
2. **Apify credential.** In `Read new roles`, create an *Apify API* credential with your token.
3. **Sheet.** Create a Google Sheet with two tabs named exactly `Jobs` and `Signals`. They can be empty: column headers are added on the first run. In both Google Sheets nodes, connect a *Google Sheets OAuth2* credential and pick the spreadsheet under *Document*.
4. Click *Test workflow* once, check both tabs, then set the workflow to *Active*. The schedule uses the workflow's timezone (*Workflow settings → Timezone*).

If you change `maxJobs`, set *Maximum Cost per Run (USD)* in `Read new roles` to `maxJobs × 0.003`.

## Expected output

The sample watchlist (Stripe on Greenhouse, Spotify on Lever, Linear on Ashby, bunq on Recruitee and 1KOMMA5° on Personio), read locally from the live public feeds on 24 Nov 2026, gave 86 roles in the 7-day window and these `Signals` rows:

| company | roles_posted | top_departments | top_countries | remote_roles |
|---|---|---|---|---|
| Stripe | 59 | 1185 Account Executives (EMEA) (6), 1195 Account Executives (APAC) (6), ... | US (30), IE (9), GB (4) | 14 |
| 1KOMMA5° Technology GmbH | 15 | Finance (2), Operations (2), Purchasing & Logistics (2) | DE (10) | 4 |
| spotify | 9 | Engineering (3), Content (2), Advertising (1) | GB (4), SE (3), US (3) | 2 |
| bunq | 3 | Support & Operations (2), Content & Design (1) | BG (1), NL (1), TR (1) | 0 |

Linear posted no roles in that window, so it got no row. `Jobs` columns are: id, company, title, department, location, country, remote, salary_min, salary_max, salary_currency, salary_period, posted_at, url, board and last_seen.

## Cost

You pay $0.003 for each role returned, with no start fee. Boards that are missing or fail are not charged. Because of the 7-day filter, cost follows each company's hiring volume, not the size of its board.

| Scenario | Roles per run | Cost |
|---|---|---|
| Sample watchlist, 5 companies (measured 24 Nov 2026) | 86 | $0.26 a week, about $1.12 a month |
| 20 companies of similar size (estimate, 4 times the above) | about 340 | about $1.03 a week, about $4.50 a month |

The estimates come from one 7-day snapshot. One big employer can dominate the total: Stripe was 59 of the 86 roles. `maxJobs` (500 = $1.50) and *Maximum Cost per Run (USD)* (1.5) cap a single run. On Apify's free plan, the monthly usage credit ($5 at the time of writing) covers about 1,600 roles.

## Limits

- **Eight systems only:** Greenhouse, Lever, Ashby, Workday, SmartRecruiters, Workable, Personio and Recruitee. iCIMS and LinkedIn are not supported. You list the companies yourself; the actor does not discover them.
- **The counts are published postings, not headcount.** One posting can cover several hires, and some employers post evergreen roles.
- **Gaps in Signals.** Companies with no roles in the window get no Signals row. Roles without a publish date are left out by the date filter.
- **Weekly windows can overlap.** If a run starts later than usual, a role can fall in two weekly windows. `Jobs` stays de-duplicated by `id`, but both weeks' Signals rows count it.
- **Board names and departments come from the feed.** `company` is the name the feed gives (the board name if the feed has none). Department names are the employer's own, Stripe's numeric prefixes included.
- **Missing data.** `country` and pay can be empty because only what the employer publishes is returned. A run that fails or times out stops the workflow, and nothing is written. Fix the cause and run it again: nothing is lost, because the next run reads the window again.
- **Large sheets.** The Google Sheets *Append or Update* operation reads the whole `Jobs` tab on every run. Very large tabs (tens of thousands of rows) get slow; archive old rows from time to time.
