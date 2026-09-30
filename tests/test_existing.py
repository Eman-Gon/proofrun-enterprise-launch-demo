"""Existing checks intentionally omit legacy and partner ID formats.

The demo illustrates a coverage gap, not a claim of production readiness.
Additional release-contract checks live under checks/.
"""
import json
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request


class ExistingHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        cls.origin = f"http://127.0.0.1:{port}"
        cls.process = subprocess.Popen(
            [sys.executable, "-m", "northstar", "--host", "127.0.0.1", "--port", str(port)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        cls.addClassCleanup(cls.stop_server)
        for _ in range(100):
            try:
                with urllib.request.urlopen(cls.origin + "/health", timeout=0.2) as response:
                    if response.status == 200:
                        return
            except (OSError, urllib.error.URLError):
                if cls.process.poll() is not None:
                    raise RuntimeError("Application exited during startup")
                time.sleep(0.03)
        raise RuntimeError("Application did not become healthy")

    @classmethod
    def stop_server(cls):
        if cls.process.poll() is None:
            cls.process.terminate()
            try:
                cls.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                cls.process.kill()
                cls.process.wait(timeout=3)

    def request(self, path, payload=None, *, raw=None, content_type="application/json"):
        data = raw if raw is not None else (json.dumps(payload).encode() if payload is not None else None)
        request = urllib.request.Request(self.origin + path, data=data,
                                         headers={"Content-Type": content_type})
        try:
            response = urllib.request.urlopen(request, timeout=3)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body = response.read()
            return response.status, json.loads(body) if "application/json" in response.headers.get("Content-Type", "") else body

    def test_ordinary_customer(self):
        payload = {"customer_id": "12345", "name": "Avery Chen"}
        self.assertEqual(self.request("/customers/import", payload),
                         (201, {"customer": payload, "imported": True}))

    def test_repeatable_import(self):
        payload = {"customer_id": "67890", "name": "Jordan Lee"}
        self.assertEqual(self.request("/customers/import", payload), self.request("/customers/import", payload))

    def test_object_id_rejected(self):
        self.assertEqual(self.request("/customers/import", {"customer_id": {}, "name": "Avery"}),
                         (422, {"error": "invalid_customer"}))

    def test_numeric_id_rejected(self):
        self.assertEqual(self.request("/customers/import", {"customer_id": 12345, "name": "Avery"})[0], 422)

    def test_empty_id_rejected(self):
        self.assertEqual(self.request("/customers/import", {"customer_id": "", "name": "Avery"})[0], 422)

    def test_missing_name_rejected(self):
        self.assertEqual(self.request("/customers/import", {"customer_id": "12345"})[0], 422)

    def test_invalid_name_rejected(self):
        self.assertEqual(self.request("/customers/import", {"customer_id": "12345", "name": None})[0], 422)

    def test_array_rejected(self):
        self.assertEqual(self.request("/customers/import", ["12345", "Avery"])[0], 422)

    def test_invalid_json(self):
        self.assertEqual(self.request("/customers/import", raw=b"{")[0], 400)

    def test_large_request_rejected(self):
        self.assertEqual(self.request("/customers/import", raw=b"x" * 70000)[0], 413)

    def test_content_type(self):
        self.assertEqual(self.request("/customers/import", raw=b"hello", content_type="text/plain")[0], 415)

    def test_health(self):
        self.assertEqual(self.request("/health"), (200, {"status": "ok"}))

    def test_unknown_route(self):
        self.assertEqual(self.request("/does-not-exist")[0], 404)

    def test_homepage(self):
        status, body = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"Northstar", body)


if __name__ == "__main__":
    unittest.main()
