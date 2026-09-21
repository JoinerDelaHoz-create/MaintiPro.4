"""
Automated Integration Tests for CMMS Web Server and REST API.
"""

from http.client import HTTPConnection
import json
from pathlib import Path
import sys
import threading
import time
import unittest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.web.server import create_server


class TestCMMSWebServer(unittest.TestCase):
    """Integration tests for CMMS HTTP Server & REST API endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.host = "127.0.0.1"
        cls.port = 58921  # Use a dedicated port for testing
        cls.server = create_server(cls.host, cls.port)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _get(self, path: str):
        conn = HTTPConnection(self.host, self.port)
        conn.request("GET", path)
        res = conn.getresponse()
        data = res.read()
        conn.close()
        return res.status, res.getheaders(), data

    def _post(self, path: str, payload: dict):
        conn = HTTPConnection(self.host, self.port)
        body = json.dumps(payload)
        conn.request("POST", path, body, {"Content-Type": "application/json"})
        res = conn.getresponse()
        data = res.read()
        conn.close()
        return res.status, json.loads(data.decode("utf-8"))

    def test_serve_index_html(self):
        status, headers, data = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn(b"CMMS INDUSTRIAL", data)

    def test_serve_css_and_js(self):
        status_css, _, data_css = self._get("/css/style.css")
        self.assertEqual(status_css, 200)
        self.assertIn(b"--bg-main", data_css)

        status_js, _, data_js = self._get("/js/app.js")
        self.assertEqual(status_js, 200)
        self.assertIn(b"state", data_js)

    def test_api_equipments_and_kpis(self):
        status, _, data = self._get("/api/equipments")
        self.assertEqual(status, 200)
        parsed = json.loads(data.decode("utf-8"))
        self.assertTrue(parsed["success"])
        self.assertIsInstance(parsed["equipments"], list)

        # Test KPIs
        status, _, kpi_data = self._get("/api/kpis")
        self.assertEqual(status, 200)
        kpis = json.loads(kpi_data.decode("utf-8"))
        self.assertTrue(kpis["success"])
        self.assertIn("availability_pct", kpis["kpis"])

    def test_api_iot_simulation(self):
        status, res = self._post("/api/iot/simulate", {"inject_anomaly": False})
        self.assertEqual(status, 200)
        self.assertTrue(res["success"])
        self.assertIn("temperature", res["reading"])
        self.assertEqual(res["severity"], "NORMAL")


if __name__ == "__main__":
    unittest.main()
