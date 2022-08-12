import pytest

from time import sleep
from datetime import datetime, timedelta
from dateutil import tz
from pathlib import Path

from htcollector.Graph import graph
from htcollector.Database import MeasurementDatabase, Measurement


@pytest.fixture(scope="class")
def database():
    db = MeasurementDatabase(
        database="shellyht",
        host="127.0.0.1",
        port="3306",
        user="test-user",
        password="test_secret",
    )
    return db


class TestGraph:
    def test_graph(self, database, tmp_path, capsys):
        stationid = "test-101101"
        database.names(
            stationid, "testroom1"
        )  # without a stationid mapping we never get anything back
        database.storeMeasurement(Measurement(stationid, 10, 40))
        sleep(1)
        database.storeMeasurement(Measurement(stationid, 15, 45))

        now = datetime.now(tz=tz.tzlocal())
        fivesecondsago = now - timedelta(seconds=5)

        fname = tmp_path / "graph.png"
        graph(database, fname, stationid, fivesecondsago, now)
        captured = capsys.readouterr()
        print(captured.out)
        assert Path.is_file(fname)
