function buildSensorTable(sensors) {
    //builds the sensor table

    // create empty element
    let table = $("<table>").addClass("table");
    if (!$.isEmptyObject(sensors)) {
        let header = Object.keys(sensors[Object.keys(sensors)[0]]);

        // table header
        let row = $("<tr>");
        for (const col of header) {row.append($("<th>").html(col));}
        table.append(row);
        
        // table data
        for (const [_, sensor] of Object.entries(sensors)) {
            let row = $("<tr>");
            for (const [column, value] of Object.entries(sensor)) {
                let text = value;
                // links for ids
                if (column == "id") {
                    text = $("<a>").prop("href", "/sensor/" + value).html(value);
                }
                row.append($("<td>").html(text));
            };
            table.append(row);
        }
    }
    return table
}

function buildTimedeltaButtons(
    plotName,
    sensors,
    buttons = {
        "Day" : {days: 1},
        "Week" : {days: 7},
        "Month" : {days: 31},
        "Year" : {days: 365},
        "All" : {days: 99999},
    }) {
    // create empty element
    let htmlButtons = $(document.createDocumentFragment());
    for (const key in buttons) {
        // a subfunction is required, else all would have the last button timedelta
        (function (key) {
            let btn = $("<button>")
                .prop({"id": "timedelta_button_" + key, "type": "button"})
                .addClass(["btn", "btn-primary"])
                .on("click", function() {getReadingsPlot(plotName, sensors, buttons[key]);})
                .html(key)
                .css({"margin-left":"2px", "margin-right":"2px"});
            htmlButtons.append(btn);
        }(key));
    }
    return htmlButtons;
}

function getReadings(sensors, timedelta, callback) {
    $.ajax({
        url: "/api/sensor/reading",
        headers: {
            Authorization: "Bearer " + Cookies.get("api_token"),
        },
        // example data: {sensor_id:[1, 2, ...], days: 1}
        data: Object.assign({"sensor_id": Object.keys(sensors)}, timedelta),
        success: function(readings) {
            callback(readings);
        }
    });
}

// plots the sensor readings in given timedelta
function plot(plotElem, sensors, readings) {
    let traces = extractData(sensors, readings);

    let layout = setupPlotlyLayout(sensors, traces);

    Plotly.react(plotElem, traces, layout);
}

function getReadingsPlot(plotElem, sensors, timedelta) {
    // combined function for request and plot
    getReadings(sensors, timedelta, function(readings) {
        plot(plotElem, sensors, readings);
    });
}

function getPlotLayoutType() {
    return Cookies.get("plot_layout_type") || "DEFAULT";
}

function setPlotLayoutType(type) {
    Cookies.set("plot_layout_type", type);
}

const Layout = {
    DEFAULT: 0,
    MULTI_Y: 1,
    STACKED_Y: 2,
}

function setupPlotlyLayout(sensors, traces) {
    // creates layout and  modifies traces accordingly

    // get plotType based on cookies
    let type = Layout[getPlotLayoutType()]
    let layout = {};

    if ([Layout.MULTI_Y, Layout.STACKED_Y].includes(type)) {
        // create new axes per unit
        let unitAxisMapper = {};
        let i = 0;
        let axisCounter = 0;
        for (const [_, sensor] of Object.entries(sensors)) {
            let trace = traces[i++];
            if (!(sensor.unit in unitAxisMapper)) {
                axisCounter++;
                let suffix = axisCounter == 1 ? "" : axisCounter;
                unitAxisMapper[sensor.unit] = "y" + suffix;
                layout["yaxis" + suffix] = {title: sensor.unit};
            }
            trace["yaxis"] = unitAxisMapper[sensor.unit];
        }

        if (type == Layout.STACKED_Y) {
            // stacking related config
            const splitHeight = 1.0 / axisCounter;
            i = 0;
            for (let [_, axis] of Object.entries(layout)) {
                axis["domain"] = [i * splitHeight, (i + 1) * splitHeight]
                i++;
            }
            layout["height"] = 300 + 160 * axisCounter;
        }
        else if (type == Layout.MULTI_Y) {
            // TODO: this one should be absolute, not realtive...
            // multi y realted config
            const spacing = 0.08;
            i = 0;
            for (let [_, axis] of Object.entries(layout)) {
                axis["position"] = i * spacing;
                if (i != 0) {
                    axis["overlaying"] = "y";
                }
                i++;
            }
            layout["xaxis"] = {domain: [(i-1) * spacing, 1.0]}
        }
    }

    if (!("height" in layout)) {
        layout["height"] = 460
    }

    return layout;
}

function extractData(sensors, readings) {
    // extracts the data from api responses how plotly needs it
    let traces = [];
    for (sensorId in readings) {
        let datetimes = readings[sensorId].map(function(obj) {return obj["datetime"];});
        let values = readings[sensorId].map(function(obj) {return obj["value"];});
        traces.push({x: datetimes, y: values, name: sensors[sensorId]["name"]});
    }
    return traces;
}

// extends plot every timeinterval by new values
function updatePlot(plotElem, sensors, minutes=1) {
    return setInterval(function() {
        if (!$.isEmptyObject(sensors)) {
            getReadings(sensors, {minutes: minutes}, function(readings) {
                let traces = extractData(sensors, readings);
                // transform into new standard
                let x = [],  y = [];
                for (trace of traces) {
                    x.push(trace.x);
                    y.push(trace.y);
                }
                Plotly.extendTraces(plotElem,  {x: x, y: y}, [...Array(traces.length).keys()]);
            })
        }
    }, minutes * 60000)
}
