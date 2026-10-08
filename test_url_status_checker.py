"""Tests for url_status_checker.py (uses a local HTTP server, no internet)."""
import csv
import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(__file__))
from url_status_checker import (
    check_url, check_urls, read_url_list, to_csv, to_json, to_text,
)


class Handler(BaseHTTPRequestHandler):
    def _route(self):
        if self.path == "/ok":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"fine")
        elif self.path == "/moved":
            self.send_response(301)
            self.send_header("Location", "/ok")
            self.end_headers()
        elif self.path == "/missing":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"nope")
        elif self.path == "/nohead":
            if self.command == "HEAD":
                self.send_response(405)
                self.end_headers()
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"get only")
        else:
            self.send_response(500)
            self.end_headers()

    do_GET = _route
    do_HEAD = _route

    def log_message(self, *args):
        pass


class TestURLStatusChecker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def url(self, path):
        return "http://127.0.0.1:%d%s" % (self.port, path)

    def test_200_ok(self):
        rec = check_url(self.url("/ok"))
        self.assertEqual(rec["status"], 200)
        self.assertEqual(rec["error"], "")
        self.assertGreaterEqual(rec["time_ms"], 0)

    def test_404_recorded_not_error(self):
        rec = check_url(self.url("/missing"))
        self.assertEqual(rec["status"], 404)
        self.assertEqual(rec["error"], "")

    def test_redirect_followed(self):
        rec = check_url(self.url("/moved"))
        self.assertEqual(rec["status"], 200)
        self.assertTrue(rec["redirected"])
        self.assertTrue(rec["final_url"].endswith("/ok"))

    def test_head_405_falls_back_to_get(self):
        rec = check_url(self.url("/nohead"))
        self.assertEqual(rec["status"], 200)
        self.assertEqual(rec["error"], "")

    def test_connection_refused_is_error(self):
        rec = check_url("http://127.0.0.1:1/", timeout=2)
        self.assertEqual(rec["status"], 0)
        self.assertNotEqual(rec["error"], "")

    def test_check_urls_returns_all(self):
        recs = check_urls([self.url("/ok"), self.url("/missing")],
                          timeout=5, delay=0)
        self.assertEqual(len(recs), 2)
        self.assertEqual([r["status"] for r in recs], [200, 404])

    def test_read_url_list_skips_comments_and_blanks(self):
        path = "/tmp/test-urls-%d.txt" % self.port
        with open(path, "w") as fh:
            fh.write("# comment\n\nhttp://a.example/\n  http://b.example/  \n")
        try:
            self.assertEqual(read_url_list(path),
                             ["http://a.example/", "http://b.example/"])
        finally:
            os.remove(path)

    def test_csv_output(self):
        recs = check_urls([self.url("/ok")], timeout=5, delay=0)
        rows = list(csv.DictReader(to_csv(recs).splitlines()))
        self.assertEqual(rows[0]["status"], "200")
        self.assertEqual(rows[0]["url"], self.url("/ok"))

    def test_json_output(self):
        recs = check_urls([self.url("/ok")], timeout=5, delay=0)
        data = json.loads(to_json(recs))
        self.assertEqual(data["checked"], 1)
        self.assertEqual(data["results"][0]["status"], 200)

    def test_text_output(self):
        recs = check_urls([self.url("/ok"), self.url("/missing")],
                          timeout=5, delay=0)
        out = to_text(recs)
        self.assertIn("URLs checked: 2", out)
        self.assertIn("200", out)
        self.assertIn("404", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
