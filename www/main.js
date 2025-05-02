$(document).ready(function () {
    let isMonitoring = false;  // Global flag
    let pollingPaused = false;

    // Text animations
    $('.text').textillate({
        loop: true,
        sync: true,
        in: { effect: "fadeIn" },
        out: { effect: "fadeOutUp" },
    });

    // Siriwave configuration
    var siriWave = new SiriWave({
        container: document.getElementById("siri-container"),
        width: 800,
        height: 200,
        style: "ios9",
        color: "#fff",
        speed: 0.2,
        amplitude: 1,
        autostart: true
    });

    // Siri message animation
    $('.siri-message').textillate({
        loop: true,
        sync: true,
        in: { effect: "fadeInUp", sync: true },
        out: { effect: "fadeOutUp", sync: true },
    });

    // Mic Button
    $("#MicBtn").click(function () {
        eel.playClickSound();
        $("#Oval").attr("hidden", true);
        $("#SiriWave").attr("hidden", false);
        eel.set_mic_pressed();
    });

    // Settings button
    $("#SettingsBtn").click(function () {
        $("#SettingsWindow").fadeToggle();
    });

    $("#CloseSettings").click(function () {
        $("#SettingsWindow").fadeOut();
    });

    // Gps Button
    $("#GpsBtn").click(function () {
        eel.playClickSound();
        $("#Oval").attr("hidden", false);
        $("#SiriWave").attr("hidden", true);
        eel.OpenGps("gps");
    });


    
    function updatebtns(json_flag, speak_flag) 
    {
        if(json_flag === true || speak_flag === true) 
        {
            $("#MonitorOnBtn").addClass("selected-option");
            $("#MonitorOffBtn").removeClass("selected-option");
        }
        if(json_flag === false || speak_flag === false)
        {
            $("#MonitorOffBtn").addClass("selected-option");
            $("#MonitorOnBtn").removeClass("selected-option");
        }


    }
    eel.expose(updatebtns);  // expose to Python
    

    // Poll both monitor mode and speak flag every 2 seconds
    function pollBackendStatus() {
        if (!pollingPaused) {  // Only poll if not paused
            updatebtns();

        }
    }
    

    pollBackendStatus(); // Initial call
    setInterval(pollBackendStatus, 2000); // Poll every 2 sec

    // Monitor On Button Click
    $("#MonitorOnBtn").click(function () {
        $("#Oval").attr("hidden", false);
        $("#SiriWave").attr("hidden", true);
    
        $("#MonitorOnBtn").addClass("selected-option");
        $("#MonitorOffBtn").removeClass("selected-option");
    
        eel.Set_jason_flag();
    
        pollingPaused = true;  // Pause polling
        setTimeout(() => { pollingPaused = false; }, 2000); // Resume after 2 sec
    });
    
    $("#MonitorOffBtn").click(function () {
        $("#Oval").attr("hidden", false);
        $("#SiriWave").attr("hidden", true);
    
        $("#MonitorOffBtn").addClass("selected-option");
        $("#MonitorOnBtn").removeClass("selected-option");
    
        eel.Clear_jason_flag();
    
        pollingPaused = true;  // Pause polling
        setTimeout(() => { pollingPaused = false; }, 2000); // Resume after 2 sec
    });


    // Instructions Button
    $("#InstructionsBtn").click(function () {
        $("#SettingsWindow").fadeOut();
        $("#InstructionsWindow").fadeToggle();
    });

    $("#CloseInstructionsBtn").click(function () {
        $("#InstructionsWindow").fadeOut();
    });

});
