// object
let sensors = {};

$.ajax({
    url: "/api/sensor",
    success: function(result) {
        sensors = result;

        displaySensorTable(sensors);

        plot(sensors, {days: 1});
    },
});

//displays the sensor table
function displaySensorTable(sensors) {
    if (!$.isEmptyObject(sensors)) {
        header = Object.keys(sensors[Object.keys(sensors)[0]]);
        var table = $("<table>").addClass("table");
        var row = $("<tr>");
        for (i in header) {row.append($("<th>").html(header[i]))};
        table.append(row);
        
        for (i in sensors) {
            row = $("<tr>");
            for (j in header) {
                row.append($("<td>").html(sensors[i][header[j]]));
            };
            table.append(row);
        }
        $("#sensor_table").html(table);
    }
};

// plots the sensor readings in given timedelta
function plot(sensors, timedelta) {
    //grab sensor data and plot
    if (!$.isEmptyObject(sensors)) {
        $.ajax({
            url: "api/sensor/reading",
            data: Object.assign({"sensor_id": Object.keys(sensors)}, timedelta),
            success: function(result) {
                traces = extractData(result);
                Plotly.react(
                    "plots",
                    traces,
                    {},
                    // {responsive: true}, // bugs UI when rebuild
                );
            },
        });
    }
};

// extracts the data how plotly needs it
function extractData(result) {
    traces = [];
    for (sensor_id in result) {
        datetimes = result[sensor_id].map(function(obj) {return obj["datetime"];});
        values = result[sensor_id].map(function(obj) {return obj["value"];});
        traces.push({x: datetimes, y: values, name: sensors[sensor_id]["name"]});
    }
    return traces;
}

// extends plot every minute by new values
var timer = setInterval(function() {
    if (!$.isEmptyObject(sensors)) {
        $.ajax({
            url: "api/sensor/reading",
            data: Object.assign({"sensor_id": Object.keys(sensors)}, {minutes: 1}),
            success: function(result) {
                traces = extractData(result);
                // transform into new standard
                x = []; y = [];
                for (i in traces) {
                    trace = traces[i];
                    x.push(trace.x);
                    y.push(trace.y);
                }
                Plotly.extendTraces("plots",  {x: x, y: y}, [...Array(traces.length).keys()]);
            },
        })
    }
}, 60000)
