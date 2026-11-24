import importlib.util
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


class IngestEngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        os.environ["INGEST_DATA_DIR"] = cls.folder.name
        module_path = Path(__file__).resolve().parents[1] / "backend" / "ingest_server.py"
        spec = importlib.util.spec_from_file_location("ingest_server", module_path)
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()
        os.environ.pop("INGEST_DATA_DIR", None)

    def setUp(self):
        self.engine = self.mod.Engine()

    def test_persistence_and_no_url_leak_in_list(self):
        item = self.engine.add_source({
            "name": "Sinal teste", "protocol": "rtmp",
            "url": "rtmp://example.invalid/live/test-secret"
        })
        listed = self.engine.sources()
        row = next(s for s in listed if s["id"] == item["id"])
        self.assertEqual(row["name"], "Sinal teste")
        self.assertNotIn("url", row)
        self.assertNotIn("test-secret", repr(listed))
        self.assertTrue(self.mod.DB_FILE.is_file())

    def test_protocol_url_validation(self):
        with self.assertRaises(ValueError):
            self.engine.add_source({"name":"A","protocol":"srt","url":"rtmp://example.invalid/live"})
        with self.assertRaises(ValueError):
            self.engine.add_source({"name":"A","protocol":"http","url":"http://example.invalid"})
        with self.assertRaises(ValueError):
            self.engine.add_source({"name":"A","protocol":"rtmp","url":"rtmp://example.invalid/\nhello"})

    def test_schedule_overlap_and_cancellation(self):
        source = self.engine.add_source({"name":"PGM", "protocol":"srt", "url":"srt://127.0.0.1:9000?mode=caller"})
        future = datetime.now(timezone.utc)+timedelta(hours=2)
        start = future.isoformat()
        end = (future+timedelta(minutes=30)).isoformat()
        first = self.engine.add_job({"source_id":source["id"],"program":"Jornal", "begins_at":start, "ends_at":end,"pre_seconds":60})
        self.assertEqual(first["status"],"scheduled")
        with self.assertRaises(ValueError):
            self.engine.add_job({"source_id":source["id"],"program":"Conflito", "begins_at":start, "ends_at":end})
        self.assertEqual(self.engine.cancel_job(first["id"])["status"],"canceled")
        second = self.engine.add_job({"source_id":source["id"],"program":"Agora livre", "begins_at":start, "ends_at":end})
        self.assertEqual(second["status"],"scheduled")

    def test_requires_timezone_and_future(self):
        source = self.engine.add_source({"name":"Teste","protocol":"rtmp","url":"rtmp://example.invalid/live"})
        with self.assertRaises(ValueError):
            self.engine.add_job({"source_id":source["id"],"program":"X","begins_at":"2027-01-01T10:00","ends_at":"2027-01-01T11:00"})
        past = (datetime.now(timezone.utc)-timedelta(minutes=2)).isoformat()
        with self.assertRaises(ValueError):
            self.engine.add_job({"source_id":source["id"],"program":"X","begins_at":past,"ends_at":past})

    def test_file_name_is_sanitized(self):
        self.assertEqual(self.mod.safe_name("../../Jornal Àçúcar??"), "jornal-acucar")


if __name__=="__main__":
    unittest.main()
