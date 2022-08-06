import pytest

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
