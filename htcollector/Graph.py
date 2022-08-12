from datetime import date, datetime

import matplotlib as mpl
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from matplotlib import cm
from matplotlib.colors import ListedColormap
from matplotlib.ticker import PercentFormatter

blue2red = ListedColormap(
    np.dstack((np.linspace(0, 1, 256), np.zeros(256), np.linspace(1, 0, 256)))[0]
)


def graph(
    db,
    fname,
    stationid,
    starttime,
    endtime,
    title="Indoor measurements",
    facecolor="#eedddd",
    tcolor="#d22c2b",
    hcolor="#2c2cd2",
    font="Amaranth",
    fontcolor="#d22c2b",
    **kwargs,
):
    """
    Generate a temeprature and humidity graph for a station.

    Args:
        db (MeasurementDatabase): the measurement database
        fname (str): filename or "-" for stdout
        stationid (str): the station id
        starttime (datetime): the start time
        endtime (datetime): the end time
        title (str, optional): the title of the graph. Defaults to "Indoor measurements".
        facecolor (str, optional): background color of the graph. Defaults to "#eedddd".
        tcolor (str, optional): color for line and label of the temperature. Defaults to "#d22c2b".
        hcolor (str, optional): color for line and label of the humidity. Defaults to "#2c2cd2".
        font (str, optional): font for labels and titles. Defaults to "Amaranth".
        fontcolor (str, optional): color of the labels and titles. Defaults to "#d22c2b".
    """
    data = db.retrieveMeasurements(stationid, starttime, endtime)
    # duplicate last entry and set time to endtime to extend last measurement
    data.append(data[-1])
    data[-1]["timestamp"] = endtime
    data = [
        (d["timestamp"], d["stationid"], d["temperature"], d["humidity"]) for d in data
    ]
    data = np.array(data)
    time = data[:, 0]
    temp = data[:, 2]
    hum = data[:, 3]
    fig = plt.figure(**kwargs)
    plt.title(
        f"{title} (now: {temp[-1]:.1f}°C / {hum[-1]:.1f}% )",
        fontfamily=font,
        color=fontcolor,
    )
    ax = fig.axes[0]
    ax.set_xlim(left=starttime, right=endtime)
    ax.set_ylabel("Temp (°C)", color=tcolor)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.set_facecolor(facecolor)
    ax.plot(time, temp, color=tcolor)
    ax2 = ax.twinx()
    ax2.set_ylabel("Humidity (%)", color=hcolor)
    ax2.plot(time, hum, color=hcolor)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    fig.autofmt_xdate()
    plt.savefig(fname)
