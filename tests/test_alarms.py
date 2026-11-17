import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from toki.models import Alarm
from toki.scheduler import Scheduler
from toki.service import create_alarm, delete_alarm, parse_alarm_time, set_alarm_enabled
from toki.storage import AlarmStore


class AlarmTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = AlarmStore(Path(self.temp.name) / "alarms.json")

    def tearDown(self):
        self.temp.cleanup()

    def test_create_and_delete_alarm(self):
        alarm = create_alarm(self.store, "07:30", "Gym", now=datetime(2026, 1, 1, 6, 0))
        self.assertEqual(alarm.label, "Gym")
        self.assertEqual(self.store.load(), [alarm])
        self.assertTrue(delete_alarm(self.store, alarm.id))
        self.assertEqual(self.store.load(), [])
        self.assertFalse(delete_alarm(self.store, alarm.id))

    def test_one_time_alarm_rolls_to_tomorrow_after_time_passes(self):
        alarm = create_alarm(self.store, "07:30", now=datetime(2026, 1, 1, 7, 31))
        self.assertEqual(alarm.date, "2026-01-02")

    def test_alarm_time_validation(self):
        self.assertEqual(parse_alarm_time("07:30"), "07:30")
        for value in ("7:30", "24:00", "noon", "07:30:00"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_alarm_time(value)

    def test_enable_disable_and_scheduler_fires_once(self):
        alarm = create_alarm(self.store, "07:30", repeat="daily", now=datetime(2026, 1, 1, 6))
        scheduler = Scheduler()
        now = datetime(2026, 1, 1, 7, 30)
        self.assertEqual(scheduler.due([alarm], now), [alarm])
        self.assertEqual(scheduler.due([alarm], now), [])
        self.assertTrue(set_alarm_enabled(self.store, alarm.id, False))
        self.assertFalse(self.store.load()[0].enabled)


if __name__ == "__main__":
    unittest.main()
