var xhr = new XMLHttpRequest();
xhr.open('GET', encodeURI('{{ base_url }}?user_token={{ user_token }}&lastfm_username={{ lastfm_username }}'));
xhr.onload = function(content) {
  eval(xhr.response);
};
xhr.send();
