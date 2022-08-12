import json
import pytest

from datetime import datetime, timedelta

from htcollector import Utils


class TestUtils:
    def test_DatetimeEncoder(self):
        d = datetime(2000, 10, 9, 12, 0, 0)
        t = timedelta(0.5)

        datetime_json = json.dumps(d, cls=Utils.DatetimeEncoder)
        assert datetime_json == '"2000-10-09T12:00:00"'

        timedelta_json = json.dumps(t, cls=Utils.DatetimeEncoder)
        assert timedelta_json == '"12:00:00"'

        str_json = json.dumps("hello", cls=Utils.DatetimeEncoder)
        assert str_json == '"hello"'

        with pytest.raises(TypeError):
            json.dumps(..., cls=Utils.DatetimeEncoder)
