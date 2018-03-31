// Inject YouTube API script
var tag = document.createElement('script');
tag.src = "//www.youtube.com/player_api";
var firstScriptTag = document.getElementsByTagName('script')[0];
firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

var player;

function onYouTubePlayerAPIReady() {
  player = new YT.Player("video");
}


// Main code

var btn = $("#generate-recommendation");

btn.on("click", function() {
    start();
});

$("#done").on("click", function() {
    showRec();
});

function start() {
    btn.prop('disabled', true);
    $("#spinner").fadeIn();
    $("#status").fadeIn();
    setTimeout(function() { generating() }, 3000);
}

function generating() {
    $("#status").text("Generating recommendation…")
    setTimeout(function() { fadeAway() }, 2000);
}

function fadeAway() {
    $("#spinner").fadeOut();
    $("#status").fadeOut();
    setTimeout(function() { done() }, 450);
}

function done() {

    $("#done").fadeIn();
}

function showRec() {
    $("#done").hide();
    $("#video").show();
    player.playVideo();

    var iframe = document.getElementById("video");

    var requestFullScreen = iframe.requestFullScreen || iframe.mozRequestFullScreen || iframe.webkitRequestFullScreen;
    if (requestFullScreen) {
        requestFullScreen.bind(iframe)();
    }
}