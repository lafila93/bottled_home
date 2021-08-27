function buildSensorTable(sensors) {
    //builds the sensor table

    // create empty element
    let table = $("<table>").addClass("table");
    if (!$.isEmptyObject(sensors)) {
        let header = Object.keys(sensors[Object.keys(sensors)[0]]);

        // table header
        let row = $("<tr>");
        for (i in header) {row.append($("<th>").html(header[i]));};
        table.append(row);
        
        // table data
        for (i in sensors) {
            let sensor = sensors[i]
            let row = $("<tr>");
            for (column in sensor) {
                let value = sensor[column]
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
};

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
    for (key in buttons) {
        (function (k) {
            let btn = $("<button>")
                .prop({"id": "timedelta_button_" + key, "type": "button"})
                .addClass(["btn", "btn-primary"])
                .on("click", function() {getReadingsPlot(plotName, sensors, buttons[k]);})
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
        data: Object.assign({"sensor_id": Object.keys(sensors)}, timedelta),
        success: function(readings) {
            callback(readings);
        }
    });
}

// plots the sensor readings in given timedelta
function plot(plotElem, sensors, readings) {
    let traces = extractData(readings, sensors);
    Plotly.react(
        plotElem,
        traces,
        {},
    );
}

function getReadingsPlot(plotElem, sensors, timedelta) {
    getReadings(sensors, timedelta, function(readings) {
        plot(plotElem, sensors, readings);
    });
}

// extracts the data how plotly needs it
function extractData(readings, sensors) {
    let traces = [];
    for (sensorId in readings) {
        let datetimes = readings[sensorId].map(function(obj) {return obj["datetime"];});
        let values = readings[sensorId].map(function(obj) {return obj["value"];});
        traces.push({x: datetimes, y: values, name: sensors[sensorId]["name"]});
    }
    return traces;
}

// extends plot every minute by new values
function updatePlot(plotElem, sensors) {
    return setInterval(function() {
        if (!$.isEmptyObject(sensors)) {
            getReadings(sensors, {minutes:1}, function(readings) {
                let traces = extractData(readings, sensors);
                // transform into new standard
                let x = [],  y = [];
                for (i in traces) {
                    let trace = traces[i];
                    x.push(trace.x);
                    y.push(trace.y);
                }
                Plotly.extendTraces(plotElem,  {x: x, y: y}, [...Array(traces.length).keys()]);
            })
        }
    }, 60000)
}

// builds input boxes
function buildInputBoxes(columns) {
    // create empty element
    let htmlInputs = $(document.createDocumentFragment());

    for (i in columns) {
        let cName = columns[i].name
        let cType = columns[i].type
        
        let label = $("<label>").prop("for", cName).html(cName + ":");

        let inputType = {
            "INTEGER" : "number",
            "FLOAT" : "number",
        }[cType] || "text";

        let box = $("<input>")
                .prop({"type": inputType, "name": cName, "id": cName})
                .addClass("form-control");
        box.prop("dataset").column = cName;
        if (cType == "FLOAT") {
            box.prop("step", "any");
        }

        htmlInputs.append(label).append(box).append("<br>");
    }
    return htmlInputs;
}
