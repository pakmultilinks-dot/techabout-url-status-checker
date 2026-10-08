#!/usr/bin/env python3
"""
URL Status Checker
==================

Checks a list of public URLs and saves each one's HTTP status to a CSV.

For every URL it records: the original URL, the final URL after redirects,
the status code, the reason phrase, the response time in milliseconds, and
any error (timeout, DNS failure, connection refused, ...).

It is deliberately polite: one request at a time, a normal browser user
agent, a configurable delay between requests (default 1 second), and a
timeout per request. This is a status check, not a load test: keep the
URL list small.

Usage:
    python url_status_checker.py urls.txt --output results.csv
    python url_status_checker.py https://example.com https://techabout.com --output results.csv
    python url_status_checker.py urls.txt --output results.csv --delay 2 --timeout 15

The URL list file holds one URL per line; lines starting with # are ignored.

TechAbout Python Developer task 5 - URL Status Checker (ZR-26-00754).
"""

import argparse
import csv
import io
import json
import sys
import time
import urllib.request
import urllib.error

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36 URLStatusChecker/1.0"


def read_url_list(path):
    """Read one URL per line from a file; skip blanks and # comments."""
    urls = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def check_url(url, timeout=10):
    """Check one URL. Returns a result record dict."""
    started = time.monotonic()

    def record(resp_url, status, reason, redirected, error=""):
        return {
            "url": url,
            "final_url": resp_url,
            "status": status,
            "reason": reason,
            "time_ms": int((time.monotonic() - started) * 1000),
            "redirected": redirected,
            "error": error,
        }

    def attempt(method):
        req = urllib.request.Request(url, method=method)
        req.add_header("User-Agent", USER_AGENT)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return ("ok", resp.geturl(), resp.status, resp.reason)
        except urllib.error.HTTPError as exc:
            # the server DID respond (with an error status): record the code
            final = exc.geturl() if hasattr(exc, "geturl") else url
            return ("http_error", final, exc.code, exc.reason)
        except Exception as exc:
            return ("error", url, 0, "%s: %s" % (type(exc).__name__, exc))

    kind, final_url, status, reason = attempt("HEAD")
    if kind == "http_error" and status == 405:
        # some servers reject HEAD; retry with GET
        kind, final_url, status, reason = attempt("GET")

    if kind == "error":
        return record(url, 0, "", False, error=reason)
    return record(final_url, status, reason, final_url != url)


def check_urls(urls, timeout=10, delay=1.0):
    """Check each URL in order, pausing delay seconds between requests."""
    records = []
    for i, url in enumerate(urls):
        if i > 0 and delay > 0:
            time.sleep(delay)
        records.append(check_url(url, timeout))
    return records


def to_csv(records):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=[
        "url", "final_url", "status", "reason", "time_ms",
        "redirected", "error"])
    writer.writeheader()
    writer.writerows(records)
    return buf.getvalue()


def to_json(records):
    return json.dumps({"checked": len(records), "results": records},
                      indent=2)


def to_text(records):
    lines = []
    ok = sum(1 for r in records if 200 <= r["status"] < 400 and not r["error"])
    lines.append("URLs checked: %d | OK (2xx/3xx): %d" % (len(records), ok))
    lines.append("")
    for r in records:
        if r["error"]:
            lines.append("%s -> ERROR (%s)" % (r["url"], r["error"]))
        else:
            redir = " -> %s" % r["final_url"] if r["redirected"] else ""
            lines.append("%s -> %d %s (%d ms)%s" % (
                r["url"], r["status"], r["reason"], r["time_ms"], redir))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check a list of URLs and save status codes to CSV.")
    parser.add_argument("urls", nargs="+",
                        help="URLs to check, or a .txt file with one URL per line")
    parser.add_argument("--output", default="",
                        help="Write the CSV results to this file")
    parser.add_argument("--format", choices=["csv", "json", "text"],
                        default="csv",
                        help="Output format (default: csv)")
    parser.add_argument("--timeout", type=int, default=10,
                        help="Seconds to wait per request (default: 10)")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Seconds to pause between requests (default: 1.0)")
    args = parser.parse_args(argv)

    if len(args.urls) == 1 and args.urls[0].endswith(".txt"):
        try:
            urls = read_url_list(args.urls[0])
        except FileNotFoundError:
            print("Error: file not found: %s" % args.urls[0], file=sys.stderr)
            return 1
    else:
        urls = args.urls

    if not urls:
        print("Error: no URLs to check", file=sys.stderr)
        return 1

    records = check_urls(urls, args.timeout, args.delay)

    if args.format == "json":
        out = to_json(records)
    elif args.format == "text":
        out = to_text(records)
    else:
        out = to_csv(records)

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as fh:
            fh.write(out)
        print("Checked %d URLs, results written to %s"
              % (len(records), args.output))
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
