import fileinput
import json
from datetime import datetime


def datetime_parser(json_dict):
    for (key, value) in json_dict.items():
        if type(value) == str:
            try:
                json_dict[key] = datetime.fromisoformat(value)
            except ValueError:
                pass
    return json_dict


def tohtml(m):
    return f"""
            <div class="measurement" id="{m["stationid"]}">
            <div class="station">{m["name"]}</div>
            <div class="time" data-time="{m["time"]}">{m['time']:%H:%M}</div>
            <div class="temp">{m["temperature"]}<span class="degrees">°C</span></div>
            <div class="hum">{m["humidity"]}<span class=percent>%</span></div>
            </div>"""


def getinput():
    return "".join(line for line in fileinput.input())


def process_array(s):
    ob = json.loads(s, object_hook=datetime_parser)
    return "\n".join(tohtml(m) for m in ob)


if __name__ == "__main__":
    print(process_array(getinput()))
