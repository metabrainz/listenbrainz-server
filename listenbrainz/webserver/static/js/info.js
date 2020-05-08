document.getElementById("copy-token").addEventListener("click", function() {
    var copyText = document.getElementById("auth-token");
    copyText.type = 'text';
    copyText.select();
    document.execCommand("copy");
    copyText.type = 'hidden';
});

$(document).ready(function () {
    $('.glyphicon-dropdown').click(function () {
        $(this).toggleClass("glyphicon-chevron-down").toggleClass("glyphicon-chevron-up");
    });
});
