$(document).ready(function () {


    // Display Speak Message : de badal print fy python
    eel.expose(DisplayMessage);
    function DisplayMessage(message) {
        $(".siri-message").text(message);
        $('.siri-message').textillate('start');
    }

    // showhood y display siriwave
    eel.expose(ShowHood)
    function ShowHood() {
        $("#Oval").attr("hidden", true);
        $("#SiriWave").attr("hidden", false);
    }

    // exithood y display oval
    eel.expose(ExitHood)
    function ExitHood() {
        $("#Oval").attr("hidden", false);
        $("#SiriWave").attr("hidden", true);
    }

    navigator.geolocation.getCurrentPosition(function (position) {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        eel.ReceiveLocation(lat, lon);  // Send back to Python
    });

});