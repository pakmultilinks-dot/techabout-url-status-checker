# URL Status Checker

A small Python script that checks a list of public URLs and saves each
one's HTTP status code to a CSV. Built for TechAbout task 5 (ZR-26-00754).

## What it does

For every URL it records:

- the original URL and the final URL after redirects
- the HTTP status code and reason phrase
- the response time in milliseconds
- whether a redirect happened
- any error (timeout, DNS failure, connection refused, ...)

It is deliberately polite: one request at a time, a normal browser user
agent, a pause between requests (default 1 second), and a per-request
timeout. It tries HEAD first and falls back to GET where a server rejects
HEAD. This is a status check, not a load test: keep the URL list small.

Output formats: `csv` (default), `json`, `text`.

## Usage

```bash
python url_status_checker.py urls.txt --output results.csv
python url_status_checker.py https://example.com https://techabout.com --output results.csv
python url_status_checker.py urls.txt --output results.csv --delay 2 --timeout 15
python url_status_checker.py urls.txt --output results.json --format json
```

The URL list file holds one URL per line; lines starting with `#` are
comments and are ignored.

## Sample results

`sample/urls.txt` holds 8 public URLs (TechAbout pages plus well-known
public sites). `sample/results.csv` and `sample/results.json` hold the
check from 8 Oct 2026:

- 7 x 200 OK (including redirects followed, e.g. techabout.com to
  www.techabout.com)
- 1 x 404 NOT FOUND (the intentionally missing page)

## Tests

```bash
python test_url_status_checker.py
```

10 tests against a local HTTP server (no internet needed) covering 200,
404, redirect following, HEAD-to-GET fallback, connection errors,
URL-list parsing, and all three output formats.

## Files

| File | Purpose |
|---|---|
| `url_status_checker.py` | The script |
| `test_url_status_checker.py` | 10 unit tests (local server) |
| `sample/urls.txt` | Sample URL list (8 public URLs) |
| `sample/results.csv` / `.json` | Sample results |
