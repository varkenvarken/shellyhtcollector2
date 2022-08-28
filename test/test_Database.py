from datetime import datetime, tzinfo
from time import sleep
from dateutil import tz

import pytest
from pytest import approx
from fixtures import database

from htcollector import Database

@pytest.fixture(scope="class")
def measurement(stationid):
    return Database.Measurement(stationid, 30, 65)


@pytest.fixture(scope="class")
def stationid():
    return "test-123456"


class TestNames:
    def test_names_insert(self, database):
        assert database.names("abcdef", "testroom") == {"abcdef": "testroom"}

    def test_names_list(self, database):
        assert database.names("*", "") == {"abcdef": "testroom"}

    def test_names_replace(self, database):
        assert database.names("abcdef", "testroom") == {"abcdef": "testroom"}
        assert database.names("*", "") == {"abcdef": "testroom"}


class TestMeasurements:
    def test_Measurement_init(self, stationid):
        m = Database.Measurement(stationid, 11.2, "70.5")
        assert type(m) is Database.Measurement
        assert m.humidity == approx(70.5)
        assert m.temperature == approx(11.2)
        assert m.stationid == stationid

    def test_Measurement_exceptions(self):
        with pytest.raises(ValueError):
            m = Database.Measurement("shellyht-123fed", "~11.2", 70.5)
        with pytest.raises(ValueError):
            m = Database.Measurement("shellyht-123fed", 11.2, "70.5%")
        with pytest.raises(ValueError):
            m = Database.Measurement("@shed-123fed", 11.2, 70.5)

    def test_storeMeasurement(self, measurement, database, stationid):
        database.names(
            stationid, "testroom"
        )  # without a stationid mapping we never get anything back
        n = database.storeMeasurement(measurement)
        assert n == 1
        r = database.retrieveLastMeasurement(stationid)
        assert len(r) == 1
        m = r[0]
        assert m["stationid"] == stationid

    def test_storeMeasurement_multi(self, database):
        database.names(
            "test-100001", "testroom1"
        )  # without a stationid mapping we never get anything back
        database.names(
            "test-100002", "testroom2"
        )  # without a stationid mapping we never get anything back
        database.storeMeasurement(Database.Measurement("test-100001", 10, 40))
        database.storeMeasurement(Database.Measurement("test-100002", 15, 45))
        r = database.retrieveLastMeasurement()
        assert len(r) > 1
        m1 = [m for m in r if m["stationid"] == "test-100001"]
        assert len(m1) == 1
        m2 = [m for m in r if m["stationid"] == "test-100002"]
        assert len(m2) == 1

    def test_retrieveMeasurements(self, database):
        database.names(
            "test-100001", "testroom1"
        )  # without a stationid mapping we never get anything back
        database.names(
            "test-100002", "testroom2"
        )  # without a stationid mapping we never get anything back
        start = datetime.now()
        sleep(1)
        database.storeMeasurement(Database.Measurement("test-100001", 10, 40))
        database.storeMeasurement(Database.Measurement("test-100002", 15, 45))
        r = database.retrieveMeasurements("*", start)
        assert len(r) > 1
        m1 = [m for m in r if m["stationid"] == "test-100001"]
        assert len(m1) == 1
        m2 = [m for m in r if m["stationid"] == "test-100002"]
        assert len(m2) == 1
        r = database.retrieveMeasurements("test-100001", start)
        assert len(r) == 1
        m1 = [m for m in r if m["stationid"] == "test-100001"]
        assert len(m1) == 1

    def test_retrieveDatetimeBefore(self, database):
        stationid = "mark-121212"
        start = datetime.now()
        database.storeMeasurement(Database.Measurement(stationid, 10, 40))
        sleep(1)
        dt1 = datetime.now()
        sleep(1)
        database.storeMeasurement(Database.Measurement(stationid, 15, 45))
        r = database.retrieveDatetimeBefore(stationid, dt1)
        assert type(r) is datetime
        assert r.timestamp() == approx(start.timestamp(), abs=0.1)
