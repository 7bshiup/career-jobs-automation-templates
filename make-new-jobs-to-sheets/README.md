# New jobs at target companies to Google Sheets, with an optional Slack digest (Make)

When a scheduled Apify task of the actor [career-site-jobs](https://apify.com/improved_gravity_qb7/greenhouse-lever-ashby-personio-jobs-scraper) finishes, Make adds that run's new jobs to a Google Sheet and can post a short digest to Slack. It works with Greenhouse, Lever, Ashby, Workable, Personio and Recruitee boards.

Disclosure: built and sold by the actor's owner. The actor is paid ($0.003 per job returned), and that money goes to the person who wrote this template.

**This folder contains no blueprint file.** A Make blueprint stores Make's internal module identifiers and connection metadata. Those can only be checked by building the scenario in Make and exporting it, and this template was written without using a Make account. Rather than ship a blueprint that might not import, the steps below set the scenario up module by module. The module names come from Make's Apify app page (apps.make.com/apify) and Apify's Make guide (docs.apify.com/platform/integrations/make). Field labels in Make's editor may differ slightly.

## How it works

Apify runs the task on a schedule. Each finished run triggers the scenario:

1. **Apify: Watch Task Runs** (instant trigger) fires when the task's run finishes.
2. *Filter:* status equals `SUCCEEDED`.
3. **Apify: Get Dataset Items** reads the jobs from that run's dataset. Each job becomes one bundle.
4. **Google Sheets: Add a Row** adds one row per job.
5. Optional: **Tools: Text aggregator** → **Slack: Create a Message** posts one message listing the run's jobs.

The task uses `"newJobsOnly": true`, so each run returns, and charges for, only jobs that no earlier run of the task returned. The sheet therefore gets no duplicates, and Make never has to compare against existing rows. Scheduling on the Apify side means Make spends operations only when a run has finished. It also avoids Make's limit on synchronous Apify runs: Make's Apify app page says synchronous runs time out after 120 seconds.

## Prerequisites

- A Make account (the free plan is enough to try it).
- An Apify account and API token (Apify Console → Settings → API & Integrations).
- A Google account for the Sheets connection. Optionally, a Slack workspace.

## Setup

### A. Apify task and schedule (Apify Console)

1. Open the actor `improved_gravity_qb7/greenhouse-lever-ashby-personio-jobs-scraper` and click *Save as a new task*.
2. Switch the task's input to JSON and paste this, with your own companies:
   ```json
   {
     "companies": ["greenhouse:discord", "https://jobs.lever.co/spotify", "https://tado.jobs.personio.de", "ashby:ramp"],
     "postedWithinDays": 7,
     "includeDescription": false,
     "newJobsOnly": true,
     "maxJobs": 200
   }
   ```
   Each company can be a career page URL, `system:board` or a bare board name. Optional filters are `keyword`, `country` and `remoteOnly`. Save the task.
3. Under *Schedules → Create new*, set a daily schedule (for example `0 8 * * *`) and add the task to it. Do not schedule it yet if you want to test step D by hand first.

### B. Google Sheet

Create a sheet with this header row: `id`, `company`, `title`, `location`, `country`, `remote`, `salary_min`, `salary_max`, `salary_currency`, `posted_at`, `url`.

### C. Make scenario, module by module

1. **Apify → Watch Task Runs.** *Connection*: create one and paste the Apify token into *API token*. *Webhook name*: for example `career-site-jobs new jobs`. Then choose the task from step A. Make's app page labels this field *Actor*; choose your task there.
2. **Filter** on the link after module 1. Label: `Succeeded only`. Condition: module 1's run *Status* is equal to (text) `SUCCEEDED`.
3. **Apify → Get Dataset Items.** *Connection*: the same one. *Dataset ID*: map the run's default dataset ID from module 1 (`defaultDatasetId` in the run object). *Format*: JSON. *Limit*: at least the task's `maxJobs` (200). *Offset*: 0. Leave *Data transformation* at its default.
4. **Google Sheets → Add a Row.** Connect Google, pick the spreadsheet and the sheet, and set that the table contains headers. Map each column to the field of the same name from module 3: `id`, `company`, `title`, `location`, `country`, `remote`, `salary_min`, `salary_max`, `salary_currency`, `posted_at`, `url`.
5. Optional Slack digest. Add a second route after module 3 with a *Router*, or add these after module 4:
   - **Tools → Text aggregator.** *Source module*: module 3. *Row separator*: New row. *Text*: `• <{{url}}|{{title}}> at {{company}} ({{location}})`, mapped from module 3.
   - **Slack → Create a Message.** Connect Slack, pick the channel, and set *Text* to `New jobs at your target companies:` followed by a new line and the aggregator's text. If a run returns no jobs, module 3 outputs no bundles, so nothing after it runs.
6. Turn the scenario on. Scheduling is *Immediately*, as data arrives, because the trigger is instant.

### D. Test

In Apify Console, click *Start* on the task. When the run succeeds, the scenario's history should show one execution, the sheet should gain one row per job, and the Slack message should appear if you added it. Start the task again straight away: the second run returns 0 jobs (newJobsOnly), so no rows are added.

## Expected output

With the sample input, a local read of the live public feeds on 24 Nov 2026 gave 29 jobs on the first run: 6 at Discord, 9 at Spotify, 14 at Ramp and 0 at tado. 19 of them had a pay range. An immediate rerun returns 0. Later runs return only jobs posted since the previous run. Each job becomes one sheet row, for example:

| id | company | title | location | country | remote | salary_min | salary_max | salary_currency |
|---|---|---|---|---|---|---|---|---|
| greenhouse:discord:8761356002 | Discord | Engineering Manager, Machine Learning - Safety | San Francisco Bay Area or Remote (U.S.) | US | true | 272000 | 340000 | USD |

## Cost

- **Apify:** $0.003 for each job returned, with no start fee. A run with no new jobs costs nothing, and boards that are missing or fail are not charged. Sample input: $0.09 for the first run. After that, about 4 new jobs a day, which is about $0.37 a month. That is an estimate from one 7-day snapshot; 20 companies of similar size would cost about $1.90 a month. `maxJobs` (200) caps a run at $0.60. On Apify's free plan, the monthly usage credit ($5 at the time of writing) covers about 1,600 jobs.
- **Make:** Make bills operations (credits). Each run uses roughly 1 for the trigger, 1 for Get Dataset Items and 1 for each row added, plus 2 if you added the Slack digest. Check your plan's monthly allowance at make.com/pricing.

## Limits

- **Not tested in Make.** These steps were written from the documented module names and were not run in Make. Field labels may differ slightly, and "Watch Task Runs" may also fire for runs that fail; the filter in step C2 handles that.
- **One task per scenario.** Two scenarios watching the same task get the same jobs. Two tasks are separate monitors with separate histories.
- **A failed run's jobs are not re-sent.** Jobs that a failed or timed-out run had already returned are counted as seen. Open the run in Apify Console to read them. Boards that are missing or slow do not fail a run: they are skipped and listed in the run's `RUN_SUMMARY` record.
- **What counts as "new".** A job counts as new if its id has not been returned before. A job reposted under a new id appears again. A job that is unlisted for 60 days is forgotten and shows up as new if it comes back.
- **Six systems only:** Greenhouse, Lever, Ashby, Workable, Personio and Recruitee. Workday, SmartRecruiters, iCIMS and LinkedIn are not supported. You list the companies yourself.
- **Missing data.** `country` and pay can be empty because only what the employer publishes is returned.
