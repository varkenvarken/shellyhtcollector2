import pytest

from htcollector import Database

db = None


@pytest.fixture(scope="session")
def database():
    global db
    if db is None:
        db = Database.MeasurementDatabase(
            database="shellyht",
            host="127.0.0.1",
            port="3306",
            user="test-user",
            password="test_secret",
        )
    return db
