var xhr = new XMLHttpRequest();
xhr.open('GET', encodeURI('{{ base_url }}{{ user_id }}?user_token={{ user_token }}'));
xhr.onload = function(content) {
  eval(xhr.response);
};
xhr.send();
