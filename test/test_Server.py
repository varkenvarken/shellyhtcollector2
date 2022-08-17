import pytest
from io import BytesIO as IO
from unittest import mock
from datetime import datetime, timedelta
import logging

from htcollector.Server import InterceptorHandlerFactory
from htcollector.Database import MeasurementDatabase, Measurement

logging.basicConfig(format="%(asctime)s %(message)s", level="INFO")


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


# helper class and functions to mock the activity of the
# InterceptorHandler instance we will get from the factory
class MockSocket(object):
    def getsockname(self):
        return ("sockname",)


class MockRequest(object):
    _sock = MockSocket()

    def __init__(self, path):
        self._path = path

    def makefile(self, *args, **kwargs):
        if args[0] == "rb":
            return IO(b"GET %s HTTP/1.0" % self._path)
        elif args[0] == "wb":
            return IO(b"")
        else:
            raise ValueError("Unknown file type to make", args, kwargs)


def finish(self):
    # Do not close self.wfile, so we can read its value
    self.wfile.flush()
    self.rfile.close()


def date_time_string(self, timestamp=None):
    """ Mocked date time string """
    return "DATETIME"


def version_string(self):
    """ mock the server id """
    return "BaseHTTP/x.x Python/x.x.x"


class TestInterceptor:
    def test_GET_OK(self, database, capsys):
        stationid = "testid-123456"
        interceptorhandler = InterceptorHandlerFactory.getHandler(database, "./static")

        with mock.patch.object(interceptorhandler, "finish", finish):
            with mock.patch.object(
                interceptorhandler, "date_time_string", date_time_string
            ):
                with mock.patch.object(
                    interceptorhandler, "version_string", version_string
                ):
                    with mock.patch.object(interceptorhandler, "wbufsize", lambda: 1):
                        start = datetime.now()
                        request = MockRequest(
                            b"/sensorlog?hum=70&temp=24&id=%s"
                            % bytes(stationid, "UTF-8")
                        )
                        ihinstance = interceptorhandler(
                            request, ("127.0.0.1", 12345), "testserver.example.org"
                        )
                        captured = capsys.readouterr()
                        print(captured.out)
                        assert (
                            ihinstance.wfile.getvalue()
                            == b"HTTP/1.0 200 OK\r\nServer: BaseHTTP/x.x Python/x.x.x\r\nDate: DATETIME\r\n\r\n"
                        )
                        database.names(
                            stationid, "testroom1"
                        )  # without a stationid mapping we never get anything back
                        r = database.retrieveMeasurements(stationid, start)
                        print(start, r)
                        assert len(r) == 1

    def test_GET_FORBIDDEN(self, database, capsys):
        stationid = "testid-@123456"  # contains an illegal character
        interceptorhandler = InterceptorHandlerFactory.getHandler(database, "./static")

        with mock.patch.object(interceptorhandler, "finish", finish):
            with mock.patch.object(
                interceptorhandler, "date_time_string", date_time_string
            ):
                with mock.patch.object(
                    interceptorhandler, "version_string", version_string
                ):
                    with mock.patch.object(interceptorhandler, "wbufsize", lambda: 1):
                        start = datetime.now()
                        request = MockRequest(
                            b"/sensorlog?hum=70&temp=24&id=%s"
                            % bytes(stationid, "UTF-8")
                        )
                        ihinstance = interceptorhandler(
                            request, ("127.0.0.1", 12345), "testserver.example.org"
                        )
                        captured = capsys.readouterr()
                        print(captured.out)
                        response = ihinstance.wfile.getvalue()
                        print(response)
                        assert (
                            response
                            == b"HTTP/1.0 403 Forbidden\r\nServer: BaseHTTP/x.x Python/x.x.x\r\nDate: DATETIME\r\n\r\n"
                        )
                        database.names(
                            stationid, "testroom1"
                        )  # without a stationid mapping we never get anything back
                        r = database.retrieveMeasurements(stationid, start)
                        print(start, r)
                        assert len(r) == 0

    def test_GET_SERVER_ERROR(self, database, capsys):
        stationid = "testid-654321"
        interceptorhandler = InterceptorHandlerFactory.getHandler(
            None, "./static"
        )  # no database reference will force an exception

        with mock.patch.object(interceptorhandler, "finish", finish):
            with mock.patch.object(
                interceptorhandler, "date_time_string", date_time_string
            ):
                with mock.patch.object(
                    interceptorhandler, "version_string", version_string
                ):
                    with mock.patch.object(interceptorhandler, "wbufsize", lambda: 1):
                        start = datetime.now()
                        request = MockRequest(
                            b"/sensorlog?hum=70&temp=24&id=%s"
                            % bytes(stationid, "UTF-8")
                        )
                        ihinstance = interceptorhandler(
                            request, ("127.0.0.1", 12345), "testserver.example.org"
                        )
                        captured = capsys.readouterr()
                        print(captured.out)
                        response = ihinstance.wfile.getvalue()
                        print(response)
                        assert (
                            response
                            == b"HTTP/1.0 500 Internal Server Error\r\nServer: BaseHTTP/x.x Python/x.x.x\r\nDate: DATETIME\r\n\r\n"
                        )
                        database.names(
                            stationid, "testroom1"
                        )  # without a stationid mapping we never get anything back
                        r = database.retrieveMeasurements(stationid, start)
                        print(start, r)
                        assert len(r) == 0

    def test_GET_GRAPH(self, database, capsys):
        stationid = "graphid-123456"
        interceptorhandler = InterceptorHandlerFactory.getHandler(database, "./static")

        database.names(
            stationid, "testroom1"
        )  # without a stationid mapping we never get anything back
        start = datetime.now()
        database.storeMeasurement(Measurement(stationid, 10, 40))
        with mock.patch.object(interceptorhandler, "finish", finish):
            with mock.patch.object(
                interceptorhandler, "date_time_string", date_time_string
            ):
                with mock.patch.object(
                    interceptorhandler, "version_string", version_string
                ):
                    with mock.patch.object(interceptorhandler, "wbufsize", lambda: 1):
                        start = datetime.now()
                        request = MockRequest(
                            b"/graph?id=%s" % bytes(stationid, "UTF-8")
                        )
                        ihinstance = interceptorhandler(
                            request, ("127.0.0.1", 12345), "testserver.example.org"
                        )
                        captured = capsys.readouterr()
                        print(captured.out)
                        assert ihinstance.wfile.getvalue()[:15] == b"HTTP/1.0 200 OK"

    def test_GET_HTML_all(self, database, capsys):
        stationid = "htmlid-123456"
        interceptorhandler = InterceptorHandlerFactory.getHandler(database, "./static")

        database.names(
            stationid, "htmlroom1"
        )  # without a stationid mapping we never get anything back
        start = datetime.now()
        database.storeMeasurement(Measurement(stationid, 10, 40))
        with mock.patch.object(interceptorhandler, "finish", finish):
            with mock.patch.object(
                interceptorhandler, "date_time_string", date_time_string
            ):
                with mock.patch.object(
                    interceptorhandler, "version_string", version_string
                ):
                    with mock.patch.object(interceptorhandler, "wbufsize", lambda: 1):
                        start = datetime.now()
                        request = MockRequest(b"/html")
                        ihinstance = interceptorhandler(
                            request, ("127.0.0.1", 12345), "testserver.example.org"
                        )
                        captured = capsys.readouterr()
                        print(captured.out)
                        assert ihinstance.wfile.getvalue()[:15] == b"HTTP/1.0 200 OK"

    def test_GET_HTML_specific(self, database, capsys):
        stationid = "htmlid-333333"
        interceptorhandler = InterceptorHandlerFactory.getHandler(database, "./static")

        database.names(
            stationid, "htmlroom2"
        )  # without a stationid mapping we never get anything back
        start = datetime.now()
        database.storeMeasurement(Measurement(stationid, 10, 40))
        with mock.patch.object(interceptorhandler, "finish", finish):
            with mock.patch.object(
                interceptorhandler, "date_time_string", date_time_string
            ):
                with mock.patch.object(
                    interceptorhandler, "version_string", version_string
                ):
                    with mock.patch.object(interceptorhandler, "wbufsize", lambda: 1):
                        start = datetime.now()
                        request = MockRequest(
                            b"/html?id=%s" % bytes(stationid, "UTF-8")
                        )
                        ihinstance = interceptorhandler(
                            request, ("127.0.0.1", 12345), "testserver.example.org"
                        )
                        captured = capsys.readouterr()
                        print(captured.out)
                        assert ihinstance.wfile.getvalue()[:15] == b"HTTP/1.0 200 OK"

    def test_GET_HTML_fail(self, database, capsys):
        stationid = "htmlid-666666"
        interceptorhandler = InterceptorHandlerFactory.getHandler(database, "./static")

        database.names(
            stationid, "htmlroom3"
        )  # without a stationid mapping we never get anything back
        start = datetime.now()
        database.storeMeasurement(Measurement(stationid, 10, 40))
        with mock.patch.object(interceptorhandler, "finish", finish):
            with mock.patch.object(
                interceptorhandler, "date_time_string", date_time_string
            ):
                with mock.patch.object(
                    interceptorhandler, "version_string", version_string
                ):
                    with mock.patch.object(interceptorhandler, "wbufsize", lambda: 1):
                        start = datetime.now()
                        request = MockRequest(
                            b"/html?stationid=%s" % bytes(stationid, "UTF-8")
                        )
                        ihinstance = interceptorhandler(
                            request, ("127.0.0.1", 12345), "testserver.example.org"
                        )
                        captured = capsys.readouterr()
                        print(captured.out)
                        assert (
                            ihinstance.wfile.getvalue()[:22]
                            == b"HTTP/1.0 403 Forbidden"
                        )

    def test_GET_JSON_all(self, database, capsys):
        stationid = "jsonid-123456"
        interceptorhandler = InterceptorHandlerFactory.getHandler(database, "./static")

        database.names(
            stationid, "json room1"
        )  # without a stationid mapping we never get anything back
        start = datetime.now()
        database.storeMeasurement(Measurement(stationid, 10, 40))
        with mock.patch.object(interceptorhandler, "finish", finish):
            with mock.patch.object(
                interceptorhandler, "date_time_string", date_time_string
            ):
                with mock.patch.object(
                    interceptorhandler, "version_string", version_string
                ):
                    with mock.patch.object(interceptorhandler, "wbufsize", lambda: 1):
                        start = datetime.now()
                        request = MockRequest(b"/json")
                        ihinstance = interceptorhandler(
                            request, ("127.0.0.1", 12345), "testserver.example.org"
                        )
                        captured = capsys.readouterr()
                        print(captured.out)
                        assert ihinstance.wfile.getvalue()[:15] == b"HTTP/1.0 200 OK"

    def test_GET_JSON_specific(self, database, capsys):
        stationid = "jsonid-333333"
        interceptorhandler = InterceptorHandlerFactory.getHandler(database, "./static")

        database.names(
            stationid, "json room2"
        )  # without a stationid mapping we never get anything back
        start = datetime.now()
        database.storeMeasurement(Measurement(stationid, 10, 40))
        with mock.patch.object(interceptorhandler, "finish", finish):
            with mock.patch.object(
                interceptorhandler, "date_time_string", date_time_string
            ):
                with mock.patch.object(
                    interceptorhandler, "version_string", version_string
                ):
                    with mock.patch.object(interceptorhandler, "wbufsize", lambda: 1):
                        start = datetime.now()
                        request = MockRequest(
                            b"/json?id=%s" % bytes(stationid, "UTF-8")
                        )
                        ihinstance = interceptorhandler(
                            request, ("127.0.0.1", 12345), "testserver.example.org"
                        )
                        captured = capsys.readouterr()
                        print(captured.out)
                        assert ihinstance.wfile.getvalue()[:15] == b"HTTP/1.0 200 OK"

    def test_GET_JSON_fail(self, database, capsys):
        stationid = "jsonid-666"
        interceptorhandler = InterceptorHandlerFactory.getHandler(database, "./static")

        database.names(
            stationid, "json room3"
        )  # without a stationid mapping we never get anything back
        start = datetime.now()
        database.storeMeasurement(Measurement(stationid, 10, 40))
        with mock.patch.object(interceptorhandler, "finish", finish):
            with mock.patch.object(
                interceptorhandler, "date_time_string", date_time_string
            ):
                with mock.patch.object(
                    interceptorhandler, "version_string", version_string
                ):
                    with mock.patch.object(interceptorhandler, "wbufsize", lambda: 1):
                        start = datetime.now()
                        request = MockRequest(
                            b"/json?stationid=%s" % bytes(stationid, "UTF-8")
                        )
                        ihinstance = interceptorhandler(
                            request, ("127.0.0.1", 12345), "testserver.example.org"
                        )
                        captured = capsys.readouterr()
                        print(captured.out)
                        assert (
                            ihinstance.wfile.getvalue()[:22]
                            == b"HTTP/1.0 403 Forbidden"
                        )

    def test_GET_NAME(self, database, capsys):
        stationid = "newname-123456"
        name = "NewName"

        interceptorhandler = InterceptorHandlerFactory.getHandler(database, "./static")
        with mock.patch.object(interceptorhandler, "finish", finish):
            with mock.patch.object(
                interceptorhandler, "date_time_string", date_time_string
            ):
                with mock.patch.object(
                    interceptorhandler, "version_string", version_string
                ):
                    with mock.patch.object(interceptorhandler, "wbufsize", lambda: 1):
                        start = datetime.now()
                        request = MockRequest(
                            b"/name?id=%s&name=%s"
                            % (bytes(stationid, "UTF-8"), bytes(name, "UTF-8"))
                        )
                        ihinstance = interceptorhandler(
                            request, ("127.0.0.1", 12345), "testserver.example.org"
                        )
                        captured = capsys.readouterr()
                        print(captured.out)
                        assert ihinstance.wfile.getvalue()[:15] == b"HTTP/1.0 200 OK"

        interceptorhandler = InterceptorHandlerFactory.getHandler(database, "./static")
        with mock.patch.object(interceptorhandler, "finish", finish):
            with mock.patch.object(
                interceptorhandler, "date_time_string", date_time_string
            ):
                with mock.patch.object(
                    interceptorhandler, "version_string", version_string
                ):
                    with mock.patch.object(interceptorhandler, "wbufsize", lambda: 1):
                        start = datetime.now()
                        request = MockRequest(b"/names")
                        ihinstance = interceptorhandler(
                            request, ("127.0.0.1", 12345), "testserver.example.org"
                        )
                        captured = capsys.readouterr()
                        print(captured.out)
                        assert ihinstance.wfile.getvalue()[:15] == b"HTTP/1.0 200 OK"

    def test_GET_STATIC_fail(self, database, capsys):
        interceptorhandler = InterceptorHandlerFactory.getHandler(database, "./static")

        with mock.patch.object(interceptorhandler, "finish", finish):
            with mock.patch.object(
                interceptorhandler, "date_time_string", date_time_string
            ):
                with mock.patch.object(
                    interceptorhandler, "version_string", version_string
                ):
                    with mock.patch.object(interceptorhandler, "wbufsize", lambda: 1):
                        request = MockRequest(b"/static/unknown.resource")
                        ihinstance = interceptorhandler(
                            request, ("127.0.0.1", 12345), "testserver.example.org"
                        )
                        captured = capsys.readouterr()
                        print(captured.out)
                        print(captured.err)
                        assert (
                            ihinstance.wfile.getvalue()[:22]
                            == b"HTTP/1.0 404 Not Found"
                        )

    def test_GET_STATIC_stylesheet(self, database, capsys):
        interceptorhandler = InterceptorHandlerFactory.getHandler(database, "./static")

        with mock.patch.object(interceptorhandler, "finish", finish):
            with mock.patch.object(
                interceptorhandler, "date_time_string", date_time_string
            ):
                with mock.patch.object(
                    interceptorhandler, "version_string", version_string
                ):
                    with mock.patch.object(interceptorhandler, "wbufsize", lambda: 1):
                        request = MockRequest(b"/static/css/stylesheet.css")
                        ihinstance = interceptorhandler(
                            request, ("127.0.0.1", 12345), "testserver.example.org"
                        )
                        captured = capsys.readouterr()
                        print(captured.out)
                        print(captured.err)
                        assert ihinstance.wfile.getvalue()[:15] == b"HTTP/1.0 200 OK"
