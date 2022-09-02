#  shellyhtcollector, a python module to process sensor readings from Shelly H&T devices
#
# (C) 2022 Michel Anders (varkenvarken)
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#  version: 20220902125110

from json import dumps
import mimetypes
from pathlib import Path
import re
from io import BytesIO as IO
from datetime import datetime, timedelta
from dateutil import tz
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from urllib.parse import urlparse, quote, unquote_plus, parse_qs
import cgi
import logging

from .Database import Measurement
from .Utils import DatetimeEncoder, sanitize_braces


class InterceptorHandlerFactory:
    """
    Provides a single handler that returns an InterceptorHandler(BaseHTTPRequestHandler)
    that writes measurements to the provided MeasurementDatabase.
    """

    @staticmethod
    def getHandler(db, static_directory):
        class InterceptorHandler(BaseHTTPRequestHandler):
            querypattern = re.compile(
                r"^/sensorlog\?hum=(?P<humidity>\d+(\.\d+)?)\&temp=(?P<temperature>\d+(\.\d+)?)\&id=(?P<stationid>[a-z01-9-]+)$",
                re.IGNORECASE,
            )
            htmlpattern = re.compile(
                r"^/html(\?id=(?P<stationid>[a-z01-9-]+))?$",
                re.IGNORECASE,
            )
            allpattern = re.compile(
                r"^/all$",
                re.IGNORECASE,
            )

            jsonpattern = re.compile(
                r"^/json(?P<p24>/24)?(\?id=(?P<stationid>[a-z01-9-]+))?$",
                re.IGNORECASE,
            )
            namespattern = re.compile(
                r"^/names$",
                re.IGNORECASE,
            )
            updatenamepattern = re.compile(
                r"^/name$",
                re.IGNORECASE,
            )
            staticpattern = re.compile(
                r"^(/static/(?P<resource>.*))|/$",
                re.IGNORECASE,
            )
            faviconpattern = re.compile(r"^/favicon.ico$")

            def send_response(self, code, message=None):
                """Add the response header to the headers buffer and log the
                response code.

                Overridden to leave out Server header (leaks information)
                """
                self.log_request(code)
                self.send_response_only(code, message)
                # self.send_header('Server', self.version_string())
                self.send_header("Date", self.date_time_string())

            @staticmethod
            def checkPath(path: Path):
                for p in path.parts:
                    if p in {".", ".."}:
                        raise ValueError("relative paths are forbidden")

            @staticmethod
            def getTimeseries(db, stationid):
                mark = datetime.now() - timedelta(days=1)
                mtime = db.retrieveDatetimeBefore(stationid, mark)
                return db.retrieveMeasurements(
                    stationid,
                    mtime if mtime is not None else mark,
                )

            def common_headers(self):
                """we only allow external scripts from jsdelivr"""
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net/npm/ 'unsafe-inline'; object-src 'none'; base-uri 'self'; frame-ancestors 'self';",
                )
                self.send_header("X-Content-Type-Options", "nosniff")

            def do_GET(self):
                logging.info(self.path)
                try:
                    if re.match(self.faviconpattern, self.path):
                        filepath = Path(static_directory) / "favicon.ico"
                        mime_type = mimetypes.guess_type(filepath)[0]
                        try:
                            with open(filepath, "rb") as f:
                                b = f.read()
                                self.send_response(HTTPStatus.OK)
                                self.send_header("Content-type", mime_type)
                                self.send_header("Content-Length", str(len(b)))
                                self.end_headers()
                                self.wfile.write(b)
                                return
                        except FileNotFoundError:
                            self.send_response(HTTPStatus.NOT_FOUND)
                    if m := re.match(self.querypattern, self.path):
                        measurement = Measurement(
                            m.group("stationid"),
                            m.group("temperature"),
                            m.group("humidity"),
                        )
                        db.storeMeasurement(measurement)
                        self.send_response(HTTPStatus.OK)
                    elif m := re.match(self.htmlpattern, self.path):
                        ms = db.retrieveLastMeasurement(m.group("stationid"))
                        mdivs = "\n".join(
                            f"""
                            <div class="measurement{' late' if m['deltat'].total_seconds()>24*3600 else ''}" id="{m["stationid"]}">
                            <div class="station">{m["name"]}</div>
                            <div class="time" data-time="{m["time"]}"></div>
                            <div class="temp">{m["temperature"]:.1f}<span class="degrees">°C</span></div>
                            <div class="hum">{m["humidity"]:.0f}<span class=percent>%</span></div>
                            </div>"""
                            for m in ms
                        )
                        html = bytes(
                            f"""
<html>
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="300">
<title>Temperatuur binnen</title>
<link href="static/css/stylesheet.css" rel="stylesheet"></head>
<body>
<div class="measurements">
{mdivs}
</div>
</body>
<script>document.querySelectorAll("[data-time]").forEach(function(e){{d=new Date(e.getAttribute("data-time"));e.innerHTML=d.getHours() + ":" + d.getMinutes().toString().padStart(2, '0')}})</script>
</html>
                        """,
                            "UTF-8",
                        )
                        self.send_response(HTTPStatus.OK)
                        self.send_header("Content-type", "text/html")
                        self.send_header("Content-Length", str(len(html)))
                        self.common_headers()
                        self.end_headers()
                        self.wfile.write(html)
                        return
                    elif m := re.match(self.allpattern, self.path):
                        last_measurements = db.retrieveLastMeasurement()
                        station_data = dumps(
                            last_measurements,
                            cls=DatetimeEncoder,
                        )
                        time_series = {
                            s["stationid"]: InterceptorHandler.getTimeseries(
                                db, s["stationid"]
                            )
                            for s in last_measurements
                        }
                        temperature_data_map = dumps(time_series, cls=DatetimeEncoder)

                        filepath = Path(static_directory) / "all.html"
                        try:
                            with open(filepath, "rb") as f:
                                html = f.read().decode()
                                html = sanitize_braces(html)
                                logging.info(html)
                            html = html.format(
                                station_data=station_data,
                                temperature_data_map=temperature_data_map,
                            )
                        except FileNotFoundError:
                            self.send_response(HTTPStatus.NOT_FOUND)

                        html = bytes(html, "UTF-8")
                        self.send_response(HTTPStatus.OK)
                        self.send_header("Content-type", "text/html")
                        self.send_header("Content-Length", str(len(html)))
                        self.common_headers()
                        self.end_headers()
                        self.wfile.write(html)
                        return
                    elif m := re.match(self.jsonpattern, self.path):
                        if m.group("p24") is not None:
                            mark = datetime.now() - timedelta(days=1)
                            mtime = db.retrieveDatetimeBefore(
                                m.group("stationid"), mark
                            )
                            json = bytes(
                                dumps(
                                    db.retrieveMeasurements(
                                        m.group("stationid"),
                                        mtime if mtime is not None else mark,
                                    ),
                                    cls=DatetimeEncoder,
                                ),
                                encoding="UTF-8",
                            )
                        else:
                            json = bytes(
                                dumps(
                                    db.retrieveLastMeasurement(m.group("stationid")),
                                    cls=DatetimeEncoder,
                                ),
                                encoding="UTF-8",
                            )
                        self.send_response(HTTPStatus.OK)
                        self.send_header("Content-type", "application/json")
                        self.send_header("Content-Length", str(len(json)))
                        self.common_headers()
                        self.end_headers()
                        self.wfile.write(json)
                        return
                    elif m := re.match(self.namespattern, self.path):
                        names = db.names("*")
                        names = "\n".join(
                            f'<tr><td>{s}</td><td>{n}</td><td><a href="/static/updatename.html?id={quote(s)}&name={quote(n)}">Change</a></td></tr>'
                            for s, n in names.items()
                        )
                        self.send_response(HTTPStatus.OK)
                        html = f"""<html><body>
                        <table>{names}</table>
                        </body></html>
                        """
                        self.send_header("Content-type", "text/html")
                        self.send_header("Content-Length", str(len(html)))
                        self.common_headers()
                        self.end_headers()
                        self.wfile.write(bytes(html, "UTF-8"))
                        return
                    elif m := re.match(self.staticpattern, self.path):
                        path = urlparse(m.group("resource")).path
                        filepath = Path(static_directory) / (
                            path.decode() if type(path) is bytes else path
                        )  # TODO check encoding URLs are not UTF-8?
                        try:
                            InterceptorHandler.checkPath(filepath)
                        except ValueError:
                            self.send_response_only(HTTPStatus.FORBIDDEN)
                        if filepath.is_dir():
                            filepath /= "index.html"
                        mime_type = mimetypes.guess_type(filepath)[0]
                        try:
                            with open(filepath, "rb") as f:
                                b = f.read()
                                self.send_response(HTTPStatus.OK)
                                self.send_header("Content-type", mime_type)
                                self.send_header("Content-Length", str(len(b)))
                                self.common_headers()
                                self.end_headers()
                                self.wfile.write(b)
                                return
                        except FileNotFoundError:
                            self.send_response(HTTPStatus.NOT_FOUND)
                    else:
                        self.send_response_only(HTTPStatus.FORBIDDEN)
                except Exception as e:
                    logging.exception(e)
                    self.send_response_only(HTTPStatus.INTERNAL_SERVER_ERROR)
                self.end_headers()

            def do_POST(self):
                logging.info(self.path)
                if m := re.match(self.updatenamepattern, self.path):
                    file_length = int(self.headers.get("Content-Length", -1))
                    try:
                        keyvalues = parse_qs(
                            self.rfile.read(file_length), max_num_fields=2
                        )  # encoding is assumed to be UTF-8
                    except ValueError:
                        self.send_response_only(HTTPStatus.BAD_REQUEST)
                        self.end_headers()
                        return
                    stationid = keyvalues.get(b"id", [b""])[0].decode("UTF-8")
                    name = keyvalues.get(b"name", [b""])[0].decode("UTF-8")
                    if stationid == "" or name == "":
                        self.send_response_only(HTTPStatus.BAD_REQUEST)
                        self.end_headers()
                        return
                    names = db.names(stationid, name)
                    # TODO refactor duplicate code
                    names = "\n".join(
                        f'<tr><td>{s}</td><td>{n}</td><td><a href="/static/updatename.html?id={quote(s)}&name={quote(n)}">Change</a></td></tr>'
                        for s, n in names.items()
                    )
                    self.send_response(HTTPStatus.OK)
                    html = f"""<html><body>
                    <table>{names}</table>
                    </body></html>
                    """
                    self.send_header("Content-type", "text/html")
                    self.send_header("Content-Length", str(len(html)))
                    self.common_headers()
                    self.end_headers()
                    self.wfile.write(bytes(html, "UTF-8"))
                    return

        return InterceptorHandler


class Interceptor(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(self, server_address, db, static_directory):
        super().__init__(
            server_address, InterceptorHandlerFactory.getHandler(db, static_directory)
        )
