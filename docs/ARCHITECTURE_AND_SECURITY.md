# Architecture and Security

This document describes how the reference demo is built, what it deliberately does not
do, and what would have to change before anything like it held real client research.

## Scope

LexStream On-Prem is a demonstration of an architecture, not a product, and the name is
fictional. The rulings are invented, nothing reads from a court, a regulator or a client
system, and the crawl is a simulation. The outcome estimator is a transparent teaching
model over that invented corpus. It is not legal advice and must not be used to assess a
real matter.

### Data provenance

Every ruling, authority, statute, portal, judge, inspector, party and tenant was written
for this repository (`backend/app/data/`). The source specification named real tribunals
and regulators; they were replaced by invented authorities and invented statute codes,
and every docket identifier starts with `SYN-`, so that no invented ruling can be read as
a decision of a real body. A test (`backend/tests/test_corpus.py`) fails if a record
mentions one of the real bodies named in that specification. No text, schema or code was
taken from a real case-law source or from any other product.

## Components

| Component | Responsibility |
| --- | --- |
| React single-page app | One tenant at a time; search, both streams, simulator, export link |
| Nginx | Serves the static bundle and proxies `/api/` to the backend |
| FastAPI routes | Search (snapshot and stream), estimator, ingest (crawl, state stream, reset), export |
| `TenantStore` | The tenant scoping layer: the only holder of the partitions |
| `TenantPartition` | One tenant's rulings, index, crawl run and activity log |
| `TenantIndex` | Inverted index, BM25 ranking, filters, snippets |
| Analytics | Distribution, exposure, clause ranking, trend by authority, estimator |
| `LexStreamEngine` | Orchestrates the store, the simulated crawls and the live snapshots |
| Broadcaster | Fans a tenant's snapshots out to that tenant's state-stream clients |
| Report writer | The `.xlsx` report of one tenant query |

## Tenant partitioning

Partitioning is structural, not a filter added to a shared query.

1. `TenantStore` (`backend/app/tenancy.py`) owns the partitions. Its `partition`
   method is the only way to obtain one, and an unknown ID raises `UnknownTenant`, which
   the application answers with `404 Unknown tenant.` on every route.
2. `LexStreamEngine.partition` is the single place that calls it. Search, the search
   stream, the estimator, the crawl, the state stream and the export all start from
   there. A test reads the engine source and fails if a second path to the partitions
   appears.
3. Each partition has its own `TenantIndex`. There is no index that holds two tenants'
   rulings, so no query can return a mixed result, and a filter that names another
   tenant's authority simply matches nothing.
4. The matches of a search stream are resolved before the stream starts, so every event
   of one stream belongs to one tenant.
5. State-stream subscribers are registered per tenant. A snapshot is delivered only to
   queues subscribed to the tenant it describes.
6. A crawl is started for the tenant named in its request and only ever indexes into
   that tenant's partition. The other tenant can crawl at the same time.
7. Docket identifiers carry the tenant code (`SYN-LAW-`, `SYN-IND-`), which makes a leak
   visible at a glance and easy to assert in tests and in the CI smoke test.
8. The browser keeps one state stream for the selected tenant. Switching tenant closes
   it, discards the previous snapshot, the filters and every view's local state, and
   ignores any snapshot whose tenant does not match the selection.

**This is data partitioning, not access control.** The demo has no authentication, so
the caller chooses the tenant. The layer guarantees that a request can only touch the
partition it names; it does not decide who may name it. See "Known gaps".

## Data flow

### Search

A snapshot search runs the query in the tenant's index and computes the analytics over
every match. A stream search resolves the same matches and then sends one `result` event
per ruling, pausing `LEXSTREAM_STREAM_DELAY_MS` between them, followed by one
`analytics_summary` event with the totals and the same analytics. The pause exists so the
progressive delivery is visible on a tenant's ten default rulings; it is zero in tests.

The stream is finite. A browser `EventSource` treats the end of a stream as a dropped
connection and asks again, which would replay every ruling, so the client closes the
source when the summary arrives and on the first error.

### Simulated crawl

A browser `EventSource` can only issue `GET`, so starting a crawl and watching it are two
requests. `POST /ingest/simulate-crawl` validates the body, registers the run, records
the first stage and answers `202` with the run id. The remaining stages are played by a
background task and delivered on `GET /ingest/stream`, the tenant's state stream. A
second crawl for a tenant with one running is refused with `409`. If the task stops on
an error, the run is marked `FAILED`, the failure is logged and published, and the
tenant can start a new crawl; a run is never left `RUNNING` by a crash.

`source_portal` is an enumeration of four fictional portal names. It is never a free
string or a URL, and the backend makes no network request: a test replaces the socket
functions with ones that fail and runs a full crawl. The "found" rulings come from a
deterministic sequence per tenant.

In production this stage would be a separate worker that drives a headless browser, for
example Playwright, against sources the organisation is licensed to use, with rate
limits, robots and terms-of-use checks, and provenance recorded per document. None of
that is implemented here and Playwright is not a dependency.

### State stream

Each state-stream client has its own bounded queue. The stream sends a `snapshot` event
on connect, an `update` event for every change (a crawl stage, a new ruling, a reset) and
a `heartbeat` event when nothing was published for five seconds.

Every event carries the complete live state of one tenant: corpus counters, authorities,
the current crawl run with all its stages so far, the newest rulings and the activity
log. A client is therefore consistent after one message, a dropped message cannot leave
it with a wrong picture, and a slow client can skip to the newest snapshot. The snapshot
is bounded and does not grow with the index.

### Why Server-Sent Events

Both flows go one way, from engine to screen. SSE runs over plain HTTP, passes through
proxies without special handling, and browsers reconnect on their own. Commands go
through ordinary requests, so nothing needs a bidirectional channel.

### Why a single worker

State lives in the process. Two workers would hold two different sets of partitions and
clients would see either one at random. Scaling out would require a shared index and a
shared fan-out, which this demo intentionally leaves out.

### Connection health

A proxy can keep the browser side of a stream open after the backend has died. The
client treats eight seconds without any event on the state stream as a dead connection,
shows `Reconnecting` and then `Disconnected`, and keeps retrying until it returns.

## Analytics and the estimator

Analytics are recomputed for every query from the matching rulings: the count and
percentage of each of the four outcomes, the total, median and highest financial
exposure, the five most cited clauses, and for each authority the share of rulings per
year that were upheld or ended in a compliance order, with the direction between its
first and last year.

Money is whole pounds stored as integers. Totals are integer sums; the median uses
`Decimal` and is sent as text, so an even count that ends in `.50` is exact. Percentages
are computed from exact fractions and rounded half up to one decimal. No amount passes
through a floating-point number.

The estimator is a smoothed empirical rate. For a chosen outcome it starts from the
tenant-wide rate, uses it to smooth the rate of the chosen authority and the rate of the
chosen matter, and uses the average of those two to smooth the rate of the rulings that
match both. Each smoothing step adds four notional rulings at the rate before it. The
response lists every step with its counts, the sample size and a confidence label that
depends only on the sample size. It is exact rational arithmetic, so the same input
always gives the same answer.

Its limits are stated in the UI and the API: a handful of invented rulings, no causal
meaning, and no relation to any real court or regulator.

## On-premises posture

The stack is designed to run with no outbound network access:

- no CDN assets, no web fonts, no analytics, no third-party API calls;
- `scripts/check_bundle_offline.py` fails CI if the built bundle names another origin;
- the interactive API documentation page is disabled because it would load assets from a
  public CDN (the OpenAPI schema is still served locally);
- the two containers talk over the internal Compose network and only the frontend port
  is published.

Building the images does need a registry and package indexes. An air-gapped site would
build elsewhere and import the images, or use internal mirrors.

## Security controls in this repository

| Control | Where |
| --- | --- |
| One scoping layer; tenant resolved before any work; `404` when unknown | `backend/app/tenancy.py`, `backend/app/engine.py` |
| Port bound to `127.0.0.1` only | `docker-compose.yml` |
| Backend not published to the host | `docker-compose.yml` |
| Containers run as non-root, read-only root filesystem (size-capped in-memory `/tmp` only), all capabilities dropped, `no-new-privileges` | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` |
| Health check defined once | `backend/Dockerfile` |
| Content Security Policy, `X-Frame-Options`, `nosniff`, `Referrer-Policy` | `frontend/nginx.conf` |
| No inline styles or scripts in the page (bars are SVG), so the CSP needs no `unsafe-inline` | `frontend/src/components/shared/Bar.tsx` |
| Same-origin API through the proxy, so no CORS is enabled | `frontend/nginx.conf`, `frontend/vite.config.ts` |
| Parameters validated by pattern, enumeration and length; `q` capped at 120 characters; unknown body fields rejected | `backend/app/api/schemas.py` |
| Portal restricted to a fixed list; no outbound request anywhere in the backend | `backend/app/models.py`, `backend/tests/test_crawl.py` |
| Streamed events capped; rulings per crawl and per tenant capped; request bodies capped at 64 KB | `backend/app/config.py`, `backend/app/partition.py`, `frontend/nginx.conf` |
| Bounded per-client queues | `backend/app/streaming/broadcaster.py` |
| Report cells cannot run as formulas | `backend/app/workbook/layout.py` |
| Exact dependency versions, lockfile for the frontend, monthly Dependabot | `backend/requirements.txt`, `frontend/package-lock.json`, `.github/dependabot.yml` |

### Spreadsheet formula injection

Titles and summaries are text that ends up in a workbook. A spreadsheet program treats a
cell that starts with `=`, `+`, `-` or `@` as a formula, which can exfiltrate data or
run a command when the file is opened. Every text cell goes through `safe_cell`, which
prefixes such text with an apostrophe so it is displayed, not evaluated. Leading spaces,
tabs and carriage returns do not hide a formula character from that check. Numbers are
written as numbers. The corpus here is fixed, so the risk is theoretical today; the
control is in place because a real ingestion path would carry untrusted text.

The same function drops control characters that a workbook cannot store. The report
repeats the caller's query in its heading, and without this a query holding such a
character made the export fail with a `500` instead of producing a report.

## Known gaps

These are accepted for a demo and would be blockers anywhere else.

- **No authentication or authorisation.** The tenant is whatever the caller sends. Anyone
  who can reach the port can read either tenant, start a crawl for either tenant and
  reset the corpus. This is why the port is bound to localhost, and why the partitioning
  layer is described as partitioning and nothing more.
- **Partitioning is in-process.** One Python process holds both tenants. A bug in shared
  code, or a memory disclosure, crosses the boundary; a database or a process per tenant
  would not have that property.
- **No TLS.** Traffic is plain HTTP.
- **No rate limiting and no cap on stream connections.** A client can open many streams
  or run many searches.
- **No persistence or audit trail.** Crawled rulings and the activity log are lost on
  restart, and nothing records who searched for what.
- **Search can be made to work hard.** A prefix query scans the vocabulary. The corpus
  cap keeps that small here; a large index would need a sorted term dictionary.
- **Build tooling advisory.** `npm audit` reports a regular-expression denial-of-service
  advisory in `picomatch`, a glob matcher used by the build tool. It runs only at build
  time against patterns from this repository and is not shipped to the browser.
  `npm audit --omit=dev` reports no advisories for runtime dependencies.

## What a real deployment would add

- **Identity first.** Single sign-on against the organisation's directory, with the
  tenant derived from the verified session and never from a parameter, plus roles inside
  a tenant (matter teams, ethical walls).
- **Stronger separation**: a database or schema per tenant with row-level security as a
  second layer, per-tenant encryption keys, and tests that run as one tenant and try to
  reach another on every release.
- **Real ingestion**: an isolated crawl worker (a headless browser such as Playwright)
  limited to licensed sources, with source, licence and retrieval date recorded for
  every document, deduplication and a human review queue.
- **A persistent search engine**, for example PostgreSQL full-text search or a dedicated
  engine deployed on site, with stemming, phrase queries and per-language analysis.
- **An audit trail**: who searched, opened or exported what, kept for the period the
  organisation's professional rules require.
- **TLS** terminated at the proxy with certificates from the site authority, and rate
  limits per user.
- **A validated model or none.** Any outcome statistic shown to practitioners needs a
  defined population, measured calibration on held-out decisions, review by
  practitioners, and wording agreed with the risk function. An untested estimate is
  worse than no estimate.
- **No simulator.** The simulated crawl and the reset exist only for the demo.
