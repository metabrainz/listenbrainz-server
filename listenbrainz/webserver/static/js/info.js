document.getElementById("copy-token").addEventListener("click", function() {
    document.getElementById("auth-token").select();
    document.execCommand("copy");
});
