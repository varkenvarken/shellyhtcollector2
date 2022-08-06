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
#  version: 20220806080222

import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .Database import Measurement


class InterceptorHandlerFactory:
    """
    Provides a single handler that returns an InterceptorHandler(BaseHTTPRequestHandler)
    that writes measurements to the provided MeasurementDatabase.
    """

    @staticmethod
    def getHandler(db):
        class InterceptorHandler(BaseHTTPRequestHandler):
            querypattern = re.compile(
                r"^/sensorlog\?hum=(?P<humidity>\d+(\.\d+)?)\&temp=(?P<temperature>\d+(\.\d+)?)\&id=(?P<stationid>[a-z01-9-]+)$",
                re.IGNORECASE,
            )

            def do_GET(self):
                print(self.path)
                if m := re.match(self.querypattern, self.path):
                    print("match", m.groupdict())
                    try:
                        measurement = Measurement(
                            m.group("stationid"),
                            m.group("temperature"),
                            m.group("humidity"),
                        )
                        db.storeMeasurement(measurement)
                        self.send_response(HTTPStatus.OK)
                    except Exception as e:
                        print(e)
                        self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                        raise
                else:
                    self.send_response(HTTPStatus.FORBIDDEN)
                self.end_headers()

        return InterceptorHandler


class Interceptor(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(self, server_address, db):
        super().__init__(server_address, InterceptorHandlerFactory.getHandler(db))
