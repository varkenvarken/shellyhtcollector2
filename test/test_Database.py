import pytest
from pytest import approx

from shellyhtcollector import Database


@pytest.fixture(scope="class")
def database():
    db = Database.MeasurementDatabase(
        database="shellyht",
        host="127.0.0.1",
        port="3306",
        user="test-user",
        password="test_secret",
    )
    return db


class TestNames:
    def test_names_insert(self, database):
        assert database.names("abcdef", "testroom") == []

    def test_names_list(self, database):
        assert database.names("*", "") == [("abcdef", "testroom")]

    def test_names_replace(self, database):
        assert database.names("abcdef", "testroom") == []
        assert database.names("*", "") == [("abcdef", "testroom")]


class TestMeasurements:
    def test_Measurement_init(self):
        stationid = "shellyht-123fed"
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
