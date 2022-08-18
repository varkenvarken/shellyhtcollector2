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
#  version: 20220818105605

from json import dumps
import mimetypes
from pathlib import Path
import re
from io import BytesIO as IO
from datetime import datetime, timedelta
from dateutil import tz
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import logging

from .Database import Measurement
from .Graph import graph
from .Utils import DatetimeEncoder


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
            graphpattern = re.compile(
                r"^/graph\?id=(?P<stationid>[a-z01-9-]+)$",
                re.IGNORECASE,
            )
            htmlpattern = re.compile(
                r"^/html(\?id=(?P<stationid>[a-z01-9-]+))?$",
                re.IGNORECASE,
            )
            jsonpattern = re.compile(
                r"^/json(\?id=(?P<stationid>[a-z01-9-]+))?$",
                re.IGNORECASE,
            )
            namespattern = re.compile(
                r"^(/name\?id=(?P<stationid>[a-z01-9-]+)\&name=(?P<name>([a-z01-9-]|\s)+))|(/names)$",
                re.IGNORECASE,
            )
            staticpattern = re.compile(
                r"^/static/(?P<resource>.+)$",
                re.IGNORECASE,
            )

            def do_GET(self):
                logging.info(self.path)
                try:
                    if m := re.match(self.querypattern, self.path):
                        measurement = Measurement(
                            m.group("stationid"),
                            m.group("temperature"),
                            m.group("humidity"),
                        )
                        db.storeMeasurement(measurement)
                        self.send_response(HTTPStatus.OK)
                    elif m := re.match(self.graphpattern, self.path):
                        now = datetime.now(tz=tz.tzlocal())
                        yesterday = now - timedelta(1)
                        f = IO(b"")
                        graph(db, f, m.group("stationid"), yesterday, now)
                        png = f.getvalue()
                        self.send_response(HTTPStatus.OK)
                        self.send_header("Content-type", "image/png")
                        self.send_header("Content-Length", str(len(png)))
                        self.end_headers()
                        self.wfile.write(png)
                        f.close()
                        return
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
                        style = """
                        .body {width:100%; }
                        .measurements {width: 90%;}
                        .measurement {float:left; width:200px;}
                        .station {float:left; font-size:16pt;}
                        .time {float:left; font-size:12pt;}
                        .temp {float:left; clear:both; font-size:40pt;}
                        .hum {float:left; font-size:12pt;}
                        .late { background-color:red; }
                        """
                        html = bytes(
                            f"""<html>
                        <head><meta charset="UTF-8"><meta http-equiv="refresh" content="300"><title>Temperatuur binnen</title>
                        <style>{style}</style>
                        </head>
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
                        self.end_headers()
                        self.wfile.write(html)
                        return
                    elif m := re.match(self.jsonpattern, self.path):
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
                        self.end_headers()
                        self.wfile.write(json)
                        return
                    elif m := re.match(self.namespattern, self.path):
                        if not self.path.startswith("/names"):
                            stationid = m.group("stationid")
                            name = m.group("name")
                            result = db.names(stationid, name)
                        names = db.names("*")
                        names = "\n".join(
                            f"<tr><td>{n[0]}</td><td>{n[1]}</td></tr>" for n in names
                        )
                        self.send_response(HTTPStatus.OK)
                        html = f"""<html><body>
                        <table>{names}</table>
                        </body></html>
                        """
                        self.send_header("Content-type", "text/html")
                        self.send_header("Content-Length", str(len(html)))
                        self.end_headers()
                        self.wfile.write(bytes(html, "UTF-8"))
                        return
                    elif m := re.match(self.staticpattern, self.path):
                        filepath = Path(static_directory) / m.group("resource")
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
                    else:
                        self.send_response(HTTPStatus.FORBIDDEN)
                except Exception as e:
                    logging.exception(e)
                    self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                self.end_headers()

        return InterceptorHandler


class Interceptor(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(self, server_address, db, static_directory):
        super().__init__(
            server_address, InterceptorHandlerFactory.getHandler(db, static_directory)
        )
