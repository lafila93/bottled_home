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
        "Day" : 60*60*24,
        "Week" : 60*60*24*7,
        "Month" : 60*60*24*31,
        "Year" : 60*60*24*365,
        "All" : 6e10,
    }) {
    // create empty element
    let htmlButtons = $(document.createDocumentFragment());
    for (const key in buttons) {
        // a subfunction is required, else all would have the last button timedelta
        (function (key) {
            let btn = $("<button>")
                .prop({"id": "timedelta_button_" + key, "type": "button"})
                .addClass(["btn", "btn-primary"])
                .on("click", function() {
                    getReadings(sensors, buttons[key], function(readings) {
                        plot(plotName, sensors, readings);
                    }, parsePlotConfigs().timeinterval)
                })
                .html(key)
                .css({"margin-left":"2px", "margin-right":"2px"});
            htmlButtons.append(btn);
        }(key));
    }
    return htmlButtons;
}

function parsePlotConfigs() {
    return {
        layout: $("input[name=plot_layout]:checked").val() || "DEFAULT",
        timeinterval: $("input[name=plot_timeinterval]:checked").val() || null,
    }
}

function getReadings(
        sensors, 
        timedelta, 
        callback, 
        timeinterval=null, 
        timeinterval_function=null) {
    let data = {
        "sensor_id": Object.keys(sensors),
        "timedelta" : timedelta,
    };

    if (timeinterval) {
        data["timeinterval"] = timeinterval;
    }
    if (timeinterval_function) {
        data["timeinterval_function"] = timeinterval_function;
    }

    $.ajax({
        url: "/api/sensor/reading",
        data: data,
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


function getPlotCookie() {
    let data = JSON.parse(Cookies.get("plot") || "{}");
    if ($.isEmptyObject(data)) {
        data = {
            layout: "DEFAULT",
            timeinterval: null
        };
        Cookies.set("plot", JSON.stringify(data));
    }

    return data;
}

function setPlotCookieKey(key, value) {
    let data = getPlotCookie();
    data[key] = value;
    Cookies.set("plot", JSON.stringify(data));
}

const Layout = {
    DEFAULT: 0,
    MULTI_Y: 1,
    STACKED_Y: 2,
}

function setupPlotlyLayout(sensors, traces) {
    // creates layout and  modifies traces accordingly

    // get plot layout based on cookies
    let plot_layout = Layout[parsePlotConfigs().layout]
    let layout = {};

    if ([Layout.MULTI_Y, Layout.STACKED_Y].includes(plot_layout)) {
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

        if (plot_layout == Layout.STACKED_Y) {
            // stacking related config
            const splitHeight = 1.0 / axisCounter;
            i = 0;
            for (let [_, axis] of Object.entries(layout)) {
                axis["domain"] = [i * splitHeight, (i + 1) * splitHeight]
                i++;
            }
            layout["height"] = 300 + 160 * axisCounter;
        }
        else if (plot_layout == Layout.MULTI_Y) {
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
function updatePlot(plotElem, sensors, seconds=60) {
    return setInterval(function() {
        if (!$.isEmptyObject(sensors)) {
            getReadings(sensors, seconds, function(readings) {
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
    }, seconds * 1000)
}
