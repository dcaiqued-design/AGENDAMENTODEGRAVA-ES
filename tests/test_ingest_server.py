import importlib.util
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch


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

class ChannelIntegrationTest(IngestEngineTest):
    def test_channel_binding_persists_and_does_not_expose_url(self):
        s = self.engine.add_source({'name':'Canal persistente','protocol':'rtmp','url':'rtmp://example.invalid/live/secret'})
        self.engine.bind_channel({'slot':0,'source_id':s['id']})
        self.assertIn({'slot':0,'source_id':s['id']}, self.mod.Engine().channel_map())
        self.assertNotIn('secret', repr(self.engine.channel_map()))
        with self.assertRaises(ValueError):
            self.engine.bind_channel({'slot':1,'source_id':s['id']})
        with self.assertRaises(ValueError):
            self.engine.bind_channel({'slot':4,'source_id':s['id']})
        with self.assertRaises(ValueError):
            self.engine.bind_channel({'slot':0,'source_id':'missing'})

    def test_cannot_replace_channel_while_recording(self):
        a=self.engine.add_source({'name':'A','protocol':'rtmp','url':'rtmp://example.invalid/a'})
        b=self.engine.add_source({'name':'B','protocol':'srt','url':'srt://example.invalid:9000'})
        self.engine.bind_channel({'slot':2,'source_id':a['id']})
        self.engine.active['test']={'source_id':a['id']}
        with self.assertRaises(ValueError):
            self.engine.bind_channel({'slot':2,'source_id':b['id']})
        self.engine.active.clear()


    def test_stop_and_dashboard_agree_when_output_is_missing(self):
        source = self.engine.add_source({
            "name": "Sem mídia", "protocol": "rtmp",
            "url": "rtmp://example.invalid/live/sintetico"
        })
        process = Mock(returncode=0)
        process.poll.return_value = None
        self.engine.spawn = Mock(return_value=process)
        with patch.object(self.mod, "ffmpeg_available", return_value=True):
            rec = self.engine.start(source["id"])
        result = self.engine.stop(rec["id"])
        row = next(r for r in self.engine.dashboard()["recordings"] if r["id"] == rec["id"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(row["status"], "failed")
        self.assertFalse(row["downloadable"])
        self.assertIsNone(self.engine.download_path(rec["id"]))

    def test_completed_file_metadata_and_removal(self):
        source = self.engine.add_source({
            "name": "Mídia de teste", "protocol": "srt",
            "url": "srt://example.invalid:9000?mode=caller"
        })
        process = Mock(returncode=0)
        process.poll.return_value = None
        self.engine.spawn = Mock(return_value=process)
        with patch.object(self.mod, "ffmpeg_available", return_value=True):
            rec = self.engine.start(source["id"])
        path = Path(rec["file_path"])
        path.write_bytes(bytes(2048))
        self.assertEqual(self.engine.stop(rec["id"])["status"], "completed")
        self.assertEqual(self.engine.download_path(rec["id"]), path)
        before = next(r for r in self.engine.recordings() if r["id"] == rec["id"])
        self.assertEqual(before["file_size_bytes"], 2048)
        self.assertTrue(before["downloadable"])
        self.assertGreaterEqual(before["duration_seconds"], 0)
        path.unlink()
        after = next(r for r in self.engine.recordings() if r["id"] == rec["id"])
        self.assertIsNone(after["file_size_bytes"])
        self.assertFalse(after["downloadable"])


if __name__ == "__main__":
    unittest.main()
