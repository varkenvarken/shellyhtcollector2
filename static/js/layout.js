let width, height, gradient;

const chartAreaBorder = {
    id: 'chartAreaBorder',
    beforeDraw(chart, args, options) {
        const { ctx, chartArea: { left, top, width, height } } = chart;
        ctx.save();
        ctx.strokeStyle = options.borderColor;
        ctx.lineWidth = options.borderWidth;
        ctx.setLineDash(options.borderDash || []);
        ctx.lineDashOffset = options.borderDashOffset;
        ctx.strokeRect(left, top, width, height);
        ctx.restore();
    }
};

function datedisplay(s) {
    d = new Date(s);
    return d.getHours() + ":" + d.getMinutes().toString().padStart(2, '0');
}

function getGradient(ctx, chartArea) {
    const chartWidth = chartArea.right - chartArea.left;
    const chartHeight = chartArea.bottom - chartArea.top;
    if (gradient === null || width !== chartWidth || height !== chartHeight) {
        // Create the gradient because this is either the first render
        // or the size of the chart has changed
        width = chartWidth;
        height = chartHeight;
        gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
        gradient.addColorStop(0, "blue");
        gradient.addColorStop(0.33, "green");
        gradient.addColorStop(0.66, "yellow");
        gradient.addColorStop(1, "red");
    }

    return gradient;
};

function sparkline(ctx, stationid) {
    // extend the last measurement to now
    temperature_data = temperature_data_map[stationid];
    last_point = structuredClone(temperature_data.slice(-1))[0]; // a slice returns an shallow array
    last_point.timestamp = new Date().toISOString();
    temperature_data.push(last_point);

    const myChart = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [{
                data: temperature_data,
                fill: false,
                pointRadius: 0,
                spanGaps: true,
                tension: 0.5
            }]
        },
        plugins: [chartAreaBorder],
        options: {
            parsing: {
                xAxisKey: 'timestamp',
                yAxisKey: 'temperature'
            },
            scales: {
                x: {
                    type: 'time',
                    //display: false,
                    time: { displayFormats: { hour: 'HH' }, unit: 'hour', unitStepSize: 6, },
                    min: new Date(Date.now() - 86400 * 1000).toISOString(),
                    max: new Date().toISOString(),
                    grid: { color: '#C0C0C0' },
                    ticks: { stepSize: 6 },
                },
                y: {
                    display: false,
                    suggestedMin: 0,
                    suggestedMax: 35,
                }
            },
            events: [],
            borderColor: function (context) {
                const chart = context.chart;
                const { ctx, chartArea } = chart;

                if (!chartArea) {
                    // This case happens on initial chart load
                    return null;
                }
                return getGradient(ctx, chartArea);
            },
            borderWidth: 1.5,
            responsive: false,
            plugins: {
                legend: {
                    display: false,
                    labels: {
                        display: false
                    }
                },
                tooltips: {
                    display: false
                },
                chartAreaBorder: {
                    borderColor: '#a0a0a0',
                    borderWidth: 2,
                },
            },
        }
    });
}

$.each(station_data, function (index, element) {
    station = `<div class="station">${element.name}</div>`;
    time = `<div class="time" data-time="${element.time}">${datedisplay(element.time)}</div>`;
    temp = `<div class="temp">${Number(element.temperature).toFixed(1)}<span class="degrees">°C</span></div>`;
    hum = `<div class="hum">${element.humidity}<span class=percent>%</span></div>`;
    canvasid = "canvas-" + element.stationid;
    spark = `<div><canvas height="120" width="180" id="${canvasid}"></canvas></div>`;
    measurement = `<div class="measurement" id="${element.stationid}">${station}${time}${temp}${hum}${spark}</div>`;
    $("#measurements").append(measurement);
    sparkline($(`#${canvasid}`)[0].getContext('2d'), element.stationid);
});
