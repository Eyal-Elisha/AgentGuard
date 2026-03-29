import unittest
from datetime import datetime, timedelta, timezone

from backend.serializers import iso_z
from backend.storage.db import _dt_iso


class SerializerTestCase(unittest.TestCase):
    def test_datetime_storage_and_serialization_normalize_to_utc(self):
        aware_dt = datetime(2026, 3, 25, 14, 30, tzinfo=timezone.utc)
        self.assertEqual(_dt_iso(aware_dt), "2026-03-25T14:30:00Z")
        self.assertEqual(iso_z("2026-03-25T14:30:00+00:00"), "2026-03-25T14:30:00Z")
        self.assertEqual(iso_z("2026-03-25T14:30:00Z"), "2026-03-25T14:30:00Z")

        naive_utc = datetime(2026, 3, 25, 14, 30)
        self.assertEqual(iso_z(naive_utc), "2026-03-25T14:30:00Z")

        jst = timezone(timedelta(hours=9))
        self.assertEqual(iso_z(datetime(2026, 3, 25, 23, 30, tzinfo=jst)), "2026-03-25T14:30:00Z")


if __name__ == "__main__":
    unittest.main()
