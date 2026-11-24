# New jobs at target companies to Slack (n8n)

Every morning this asks the Apify actor [career-site-jobs](https://apify.com/improved_gravity_qb7/greenhouse-lever-ashby-personio-jobs-scraper) for jobs that appeared since its last run at the companies you list, and posts them to a Slack channel. It works with Greenhouse, Lever, Ashby, Workable, Personio and Recruitee boards.

Disclosure: built and sold by the actor's owner. The actor is paid ($0.003 per job returned), and that money goes to the person who wrote this template.

File: `workflow.json`. In n8n, open a new workflow, then paste the file contents or use *Import from File*.

## How it works

`Every day at 08:00` (Schedule Trigger) → `Run task: new jobs` (Apify node, *Actor tasks → Run task and get dataset*, input with `"newJobsOnly": true`) → `Build Slack digest` (Code) → `Post to Slack` (Slack, *Message → Send*).

- `newJobsOnly` makes the actor return, and charge for, only jobs that no earlier run of the same Apify task returned. The actor keeps that history, so n8n stores nothing.
- The digest posts one message for every 20 jobs, sorted by company, with a link, location, a remote flag and the pay range when the employer publishes one. If no jobs are new, nothing is posted.

## Prerequisites

- n8n with the Apify community node `@apify/n8n-nodes-apify` installed. Self-hosted: *Settings → Community Nodes → Install*. n8n Cloud: search "Apify" in the nodes panel; the instance owner must first allow verified community nodes. The workflow was checked against node version 0.9.1.
- An Apify account and API token (Apify Console → Settings → API & Integrations).
- A Slack workspace where you can add the n8n Slack app, or a Slack bot token.

## Setup (about 5 minutes)

1. **Create an Apify task.** In Apify Console, open the actor `improved_gravity_qb7/greenhouse-lever-ashby-personio-jobs-scraper` and choose *Save as a new task* (any name). The task is what keeps this workflow's history separate. Every workflow needs its own task.
2. **Apify credential.** Open `Run task: new jobs`, create an *Apify API* credential with your token, then choose your task under *Actor Task*.
3. **Companies and filters.** Edit *Input (JSON)* in the same node. Each company can be a career page URL, `system:board` (`greenhouse:discord`) or a bare board name:
   ```json
   {
     "companies": ["greenhouse:discord", "https://jobs.lever.co/spotify", "https://tado.jobs.personio.de", "ashby:ramp"],
     "keyword": "",
     "country": "",
     "postedWithinDays": 7,
     "remoteOnly": false,
     "includeDescription": false,
     "newJobsOnly": true,
     "maxJobs": 200
   }
   ```
   Optional filters: `keyword` (every word must be in the title, for example `"engineer"`), `country` (`"DE"` or `"Germany"`) and `remoteOnly`. Each field you set here overrides the task's saved input. Fields you leave out keep the task's values (Apify API docs, run task).
4. **Slack.** Open `Post to Slack`, connect a *Slack API* credential, and pick the channel. The bot must be a member of that channel.
5. Click *Test workflow* once, check the channel, then set the workflow to *Active*. The schedule uses the workflow's timezone (*Workflow settings → Timezone*).

## Expected output

Example message (abridged), from a local test run on 24 Nov 2026 that used the four sample companies above:

```
*29 new jobs at your target companies* (1/2)
• Account Executive, Media & Entertainment at *Discord* (Los Angeles Metropolitan Area or New York City Metropolitan Area) | USD 272,000-306,000
• Engineering Manager, Machine Learning - Safety at *Discord* (San Francisco Bay Area or Remote (U.S.), remote) | USD 272,000-340,000
...
```

In Slack each title links to the job on the company's career page.

- **First run:** every matching job posted in the last 7 days, up to `maxJobs`. That was 29 jobs on 24 Nov for the sample input: 6 at Discord, 9 at Spotify, 14 at Ramp and 0 at tado. 19 of them showed a pay range.
- **Later runs:** only jobs that are new since the previous run. An immediate rerun on the same boards returns 0, so nothing is charged or posted.

## Cost

You pay $0.003 for each job returned, with no start fee. A run with no new jobs costs nothing. Boards that are missing or fail are not charged.

| Scenario | Jobs | Cost |
|---|---|---|
| First run, the four sample companies (measured 24 Nov 2026) | 29 | $0.09 |
| Daily runs after that, same four companies (estimate: 29 jobs in 7 days, so about 4 a day) | about 125 a month | about $0.37 a month |
| 20 companies of similar size (estimate, 5 times the above) | about 620 a month | about $1.90 a month |

The estimates come from one 7-day snapshot. Hiring volume changes week to week, and one big employer can account for most of the total. Two caps limit a single run: `maxJobs` (200 = $0.60) and the node's *Maximum Cost per Run (USD)* (0.6). Raise both together. On Apify's free plan, the monthly usage credit ($5 at the time of writing) covers about 1,600 jobs.

## Limits

- **Six systems only:** Greenhouse, Lever, Ashby, Workable, Personio and Recruitee. Workday, SmartRecruiters, iCIMS and LinkedIn are not supported. You list the companies yourself; the actor does not discover them.
- **One task per workflow.** Two workflows that run the same task share one history, so each one misses jobs the other has already received. Runs started directly on the actor (without a task) share a single account-wide history.
- **A failed run loses its jobs.** If the run fails or times out, the Apify node stops the workflow. Jobs that run had already returned are counted as seen and will not be posted again; open the run in Apify Console to read them. Boards that are missing or slow do not fail a run: they are skipped and listed in the run's `RUN_SUMMARY` record.
- **What counts as "new".** A job counts as new if its id has not been returned before. A job reposted under a new id appears again. A job that is unlisted for 60 days is forgotten and shows up as new if it comes back.
- **First run.** Only jobs posted in the last 7 days count (`postedWithinDays`), so older jobs never appear. If more than `maxJobs` jobs match, the rest come in the following runs.
- **Missing data.** `country` and pay can be empty because only what the employer publishes is returned. Slack messages are capped at 20 jobs each to stay well inside Slack's message limits.
