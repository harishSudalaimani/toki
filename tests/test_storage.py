import json
import tempfile
import unittest
from pathlib import Path

from toki.models import Alarm
from toki.storage import AlarmStore, StorageError


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "alarms.json"
        self.store = AlarmStore(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_json_persistence(self):
        alarm = Alarm("abc12345", "08:00", "Work", "daily", True)
        self.store.save([alarm])
        self.assertEqual(self.store.load(), [alarm])
        self.assertEqual(json.loads(self.path.read_text()), [alarm.to_dict()])

    def test_corrupt_json_is_reported_and_left_untouched(self):
        content = "{broken"
        self.path.write_text(content)
        with self.assertRaises(StorageError):
            self.store.load()
        self.assertEqual(self.path.read_text(), content)

    def test_missing_file_is_an_empty_store(self):
        self.assertEqual(self.store.load(), [])


if __name__ == "__main__":
    unittest.main()
