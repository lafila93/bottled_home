let modes;
let currentColor = "#000000";
let currentMode;

// debug
modes = ["first mode", "second mode", "third mode"]
currentMode = modes[0]
buildModeRadio(modes, currentMode)
// debug

// get status and update webpage accordingly
$.ajax({
    url: "http://led_IoT/status",
    success: function(result) {
        modes = result["modes"];
        currentMode = result["currentMode"];
        currentColor = result["currentColor"];

        $("#color").val(currentColor);

        buildModeRadio(modes)
    },
})

// register color change -> led change
$("#color").on("change", function(event) {
    currentColor = this.value;
    setLed(currentMode, currentColor);
})

// create led mode radio
function buildModeRadio(modes, currentMode) {
    for (i in modes) {
        mode = modes[i];
        radio = $("<input>")
            .addClass("form-check-input")
            .prop("type", "radio")
            .prop("name", "modes")
            .val(mode);
        label = $("<label>")
            .addClass("form-check-label")
            .prop("for", mode)
            .html(mode);
        $("#modesRadio").append(radio).append(label).append("<br>")
    }
    // set current mode active
    $("[value='" + currentMode + "']").prop("checked", true)
    // set onchance callback
    $("[name='modes']").on("change", function() {
        if (this.checked) {
            currentMode = this.value;
            setLed(currentMode, currentColor);
        }
    });
}

function setLed(mode, color) {
    if (mode && color) {
        $.ajax({
            url: "http://led_IoT/set",
            method: "POST",
            data: {mode: mode, color: color},
            success: function(result) {
                console.log("Yay")
            },
        });
    }
}
