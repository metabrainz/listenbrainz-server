document
  .getElementById("show-hide-token")
  .addEventListener("click", function () {
    const token = document.getElementById("auth-token");
    const btn = document.getElementById("show-hide-token");

    if (token.type === "password") {
      token.type = "text";
      btn.className = "btn btn-info glyphicon glyphicon-eye-close";
      btn.title = "Hide user token";
    } else {
      token.type = "password";
      btn.className = "btn btn-info glyphicon glyphicon-eye-open";
      btn.title = "Show user token";
    }
  });

function copy(token) {
  token.select();
  document.execCommand("copy");
}

document.getElementById("copy-token").addEventListener("click", function () {
  const token = document.getElementById("auth-token");
  if (token.type === "password") {
    token.type = "text";
    copy(token);
    token.type = "password";
  }
  copy(token);
  const copyButton = document.getElementById("copy-token");
  copyButton.textContent = "Copied!";
});
