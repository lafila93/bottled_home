let sensors;

$.ajax({
    url: "/api/sensor",
    success: function(result) {
        // extract sensor names
        sensors = result.map(function(obj) {return obj["name"];})
        //write sensor data directly to document as of now
        displaySensorTable(result);

        plot(sensors, {days: 1});
    },
});

//displays the sensor table
function displaySensorTable(result) {
    if (result.length > 0) {
        header = Object.keys(result[0]);
        var table = $("<table>").addClass("table");
        var row = $("<tr>");
        for (i in header) {row.append($("<th>").html(header[i]))};
        table.append(row);
        
        for (i in result) {
            row = $("<tr>");
            for (j in header) {
                row.append($("<td>").html(result[i][header[j]]));
                //row.append("<td>" + result[i][header[j]] + "</td>");
            };
            table.append(row);
        }
        $("#sensor_table").html(table);
    }
};

// plots the sensor readings in given timedelta
function plot(sensors, timedelta) {
    //grab sensor data and plot
    if (sensors.length > 0) {
        $.ajax({
            url: "api/sensor/" + sensors.join("&"),
            data: timedelta,
            success: function(result) {
                traces = extractData(result);
                Plotly.react("plots", traces);
            },
        });
    }
};

// extracts the data how plotly needs it
function extractData(result) {
    traces = [];
    for (sensor in result) {
        datetimes = result[sensor].map(function(obj) {return obj["datetime"];});
        values = result[sensor].map(function(obj) {return obj["value"];});
        traces.push({x: datetimes, y: values, name: sensor});
    }
    return traces;
}

// extends plot every minute by new values
var timer = setInterval(function() {
    if (sensors.length > 0) {
        $.ajax({
            url: "api/sensor/" + sensors.join("&"),
            data: {minutes: 1},
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
