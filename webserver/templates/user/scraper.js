function makeURIObject(lastfmURI, spotifyURI) {

}

function select(selector, collection) {
    var newCollection = [];
    for (var i = 0; i < collection.length; i++) {
        if (selector(collection[i])) {
            newCollection.push(collection[i]);
        }
    }
    return newCollection;
}

function map(applicable, collection) {
    var newCollection = [];
    for (var i = 0; i < collection.length; i++) {
        newCollection.push(applicable(collection[i]));
    }
    return newCollection;
}

function each(applicable, collection) {
    for (var i = 0; i < collection.length; i++) {
        applicable(collection[i]);
    }
}

function isSpotifyURI(uri) {
    return !!(/open.spotify/.exec(uri));
}

function Scrobble(rootScrobbleElement) {
    this.rootScrobbleElement = rootScrobbleElement;
}

Scrobble.prototype.lastfmID = function () {
    // Returns url of type "http://www.last.fm/music/Mot%C3%B6rhead"
    if ('url' in this.rootScrobbleElement && this.rootScrobbleElement['url'] !== "" ) {
        var url = this.rootScrobbleElement['url'];
        url = url.split("/");
        return url.slice(0, parts.length-2).join("/");
    } else {
        return "";
    }
};

Scrobble.prototype.artistName = function () {
    if ('artist' in this.rootScrobbleElement && '#text' in this.rootScrobbleElement['artist']) {
        return this.rootScrobbleElement['artist']['#text'];
    } else {
        return "";
    }
};

Scrobble.prototype.trackName = function () {
    if ('name' in this.rootScrobbleElement) {
        return this.rootScrobbleElement['name'];
    } else {
        return "";
    }
};

Scrobble.prototype.scrobbledAt = function () {
    if ('date' in this.rootScrobbleElement && 'uts' in this.rootScrobbleElement['date']) {
        return this.rootScrobbleElement['date']['uts'];
    } else {
        return "";
    }
};

Scrobble.prototype.trackMBID = function () {
    if ('mbid' in this.rootScrobbleElement) {
        return this.rootScrobbleElement['mbid'];
    } else {
        return "";
    }
};

Scrobble.prototype.asJSONSerializable = function () {
    var trackjson = {
        "track_metadata": {
            "track_name": this.trackName(),
            "artist_name": this.artistName(),
            "additional_info": {
                "recording_mbid": this.trackMBID()
            }
        },
        "listened_at": this.scrobbledAt(),
    };

    // Remove keys with blank values
    (function filter(obj) {
        $.each(obj, function(key, value){
            if (value === "" || value === null){
                delete obj[key];
            } else if (Object.prototype.toString.call(value) === '[object Object]') {
                filter(value);
            } else if (Array.isArray(value)) {
                value.forEach(function (el) { filter(el); });
            }
        });
    })(trackjson);
    return trackjson;
};

function encodeScrobbles(jsonstr) {
    var scrobbles = JSON.parse(jsonstr);
    scrobbles = scrobbles['recenttracks']['track'];

    var parsedScrobbles = map(function(rawScrobble) {
        var scrobble = new Scrobble(rawScrobble);
        return scrobble.asJSONSerializable();
    }, scrobbles);

    var structure = {
        "listen_type" : "import",
        "payload"     : parsedScrobbles
    };
    return structure;
}

function getLastFMPage(page) {
    function retry(reason) {
        console.warn(reason + ' fetching last.fm page=' + page + ', retrying in 3s');
        setTimeout(function () {
            getLastFMPage(page);
        }, 3000);
    }

    var url = "http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user={{ lastfm_username }}&api_key={{ lastfm_api_key }}&format=json&page=" + page;

    var xhr = new XMLHttpRequest();
    xhr.timeout = 10 * 1000; // 10 seconds
    xhr.open("GET", encodeURI(url));
    xhr.onload = function () {
        if (/^2/.test(this.status)) {
            reportPageAndGetNext(this.response);
        } else if (/^5/.test(this.status)) {
            retry('got ' + this.status);

        } else {
            // ignore 40x
            pageDone();
        }
    };
    xhr.ontimeout = function () {
        retry('timeout');
    };
    xhr.onabort = function () {
        // this should never happen
        pageDone();
    };
    xhr.onerror = function () {
        retry('error');
    };
    xhr.send();
}

var version = "1.6";
var page = 1;
var numberOfPages = 1;

var submitQueue = [];
var isSubmitActive = false;
var rl_remain = -1;
var rl_reset = -1;

var numCompleted = 0;
var activeSubmissions = 0;

var timesReportScrobbles = 0;
var timesGetPage = 0;
var times4Error = 0;
var times5Error = 0;

function getPageCount() {
    function getCountAgain(reason) {
        console.warn(reason + ' fetching last.fm pagecount, retrying in 3s');
        setTimeout(function () {
            getPageCount();
        }, 3000);
    }
    var url = "http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user={{ lastfm_username }}&api_key={{ lastfm_api_key }}&format=json&page=1";

    var xhr = new XMLHttpRequest();
    xhr.timeout = 10 * 1000; // 10 seconds
    xhr.open("GET", encodeURI(url));
    xhr.onload = function () {
        if (/^2/.test(this.status)) {
            var temp = JSON.parse(this.response);
            if ('error' in temp) {
                updateMessage("<i class='fa fa-error'></i>" + temp['message'] + "<br><span><a href='https://listenbrainz.org/user/{{ user_id }}>Go to your ListenBrainz profile</a> | <a href='' id='close-progress-container'>Close</a></span><br><span style='font-size:8pt'>Thank you for using ListenBrainz</span>");
                completeMessage();
                return;
            }
            numberOfPages = temp['recenttracks']['@attr']['totalPages'];
            if (numberOfPages == 0) {
                updateMessage("<i class='fa fa-check'></i> Import finished<br><span><a href='https://listenbrainz.org/user/{{ user_id }}>Go to your ListenBrainz profile</a> | <a href='' id='close-progress-container'>Close</a></span><br><span style='font-size:8pt'>Thank you for using ListenBrainz</span>");
                completeMessage();
            }
            else {
                getNextPagesIfSlots();
            }
        } else if (/^5/.test(this.status)) {
            getCountAgain('COUNT-got ' + this.status);
        } else {
            // ignore 40x
            getNextPagesIfSlots();
        }
    };
    xhr.ontimeout = function () {
        getCountAgain('COUNT-timeout');
    };
    xhr.onerror = function () {
        getCountAgain('COUNT-error');
    };
    xhr.send();
}

function reportScrobbles(struct) {
    if (!struct) {
      struct = submitQueue.shift()
    }

    if (!struct.payload.length) {
        pageDone();
        return;
    }

    var current = new Date().getTime() / 1000;
    var delay = -1;

    // If we have no prior reset time or the reset time has passed, delay is 0
    if (rl_reset < 0 || current > rl_reset)
        delay = 0;
    else if (rl_remain > 0)
        delay = Math.max(0, Math.ceil((rl_reset - current) * 1000 / rl_remain));
    else
        delay = Math.max(0, Math.ceil((rl_reset - current) * 1000));

    setTimeout( function () {
            timesReportScrobbles++;
            var reportingURL = "{{ base_url }}" + "/";    //must have a trailing slash
            var xhr = new XMLHttpRequest();
            xhr.open("POST", reportingURL);
            xhr.setRequestHeader("Authorization", "Token {{ user_token }}");
            xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
            xhr.timeout = 10 * 1000; // 10 seconds
            xhr.onload = function(content) {
                rl_remain = parseInt(xhr.getResponseHeader("X-RateLimit-Remaining"));
                rl_reset = parseInt(xhr.getResponseHeader("X-RateLimit-Reset"));
                if (this.status >= 200 && this.status < 300) {
                    console.log("successfully reported page");
                    pageDone();
                } else if (this.status == 429) {
                    times4Error++;
                    // This should never happen, but if it does, toss it back in and try again.
                    reportScrobbles(struct);
                } else if (this.status >= 400 && this.status < 500) {
                    times4Error++;
                    // We mark 4xx errors as completed because we don't
                    // retry them
                    console.log("4xx error, skipping");
                    pageDone();
                } else if (this.status >= 500) {
                    console.log("received http error " + this.status + " req'ing");
                    times5Error++;
                    reportScrobbles(struct);
                } else {
                    console.log("received http status " + this.status + ", skipping");
                    pageDone();
                }

                if (numCompleted >= numberOfPages) {
                    updateMessage("<i class='fa fa-check'></i> Import finished<br><span><a href='https://listenbrainz.org/user/{{ user_id }}>Go to your ListenBrainz profile</a> | <a href='' id='close-progress-container'>Close</a></span><br><span style='font-size:8pt'>Thank you for using ListenBrainz</span>");
                    completeMessage();
                } else {
                    updateMessage("<i class='fa fa-cog fa-spin'></i> Sending page " + numCompleted + " of " + numberOfPages + " to ListenBrainz<br><span style='font-size:8pt'>Please don't navigate while this is running</span>");
                }
            };
            xhr.ontimeout = function(context) {
                console.log("timeout, req'ing");
                reportScrobbles(struct);
            }
            xhr.onabort = function(context) {
                console.log("abort, req'ing");
                reportScrobbles(struct);
            };
            xhr.onerror = function(context) {
                console.log("error, req'ing");
                reportScrobbles(struct);
            };
            xhr.send(JSON.stringify(struct));
        }, delay);
}

function completeMessage() {
    var close = document.getElementById('close-progress-container');
    close.addEventListener('click', function(ev) {
        ev.preventDefault();
        var el = document.getElementById('listen-progress-container');
        el.parentNode.removeChild(el);
    }, false);
}

function reportPageAndGetNext(response) {
    timesGetPage++;
    if (page == 1) {
        updateMessage("<i class='fa fa-cog fa-spin'></i> working<br><span style='font-size:8pt'>Please do not close this page while the process is running</span>");
    }
    var struct = encodeScrobbles(response);
    submitQueue.push(struct);
    if (!isSubmitActive) {
        isSubmitActive = true;
        reportScrobbles();
    }
    getNextPagesIfSlots();
}

function getNextPagesIfSlots() {
    // Get a new lastfm page and queue it only if there are more pages to download and we have
    // less than 10 pages waiting to submit
    while (page <= numberOfPages && activeSubmissions < 10) {
        activeSubmissions++;
        getLastFMPage(page);
        page += 1;
    }
}

function pageDone() {
    activeSubmissions--;
    numCompleted++;

    // start the next submission
    if (submitQueue.length)
        reportScrobbles();
    else
        isSubmitActive = false;
    getNextPagesIfSlots();
}

function updateMessage(message) {
    document.getElementById("listen-progress-container").innerHTML =  "" +
        "<img src='{{ url_for('static', filename='img/listenbrainz-logo.svg', _external=True) }}' height='75'><br><br>" +
        message + "<br>" +
        "<span style='display:none'>" +
        "reportedScrobbles " + timesReportScrobbles +
        ", getPage " + timesGetPage + ", number4xx " + times4Error +
        ", number5xx " + times5Error + ", page " + page + "</span>" +
        "<br><span style='font-size:6pt; position:absolute; bottom:1px; right: 3px'>v"+version+"</span>";
}

document.body.insertAdjacentHTML( 'afterbegin', '<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/font-awesome/4.4.0/css/font-awesome.min.css">');
document.body.insertAdjacentHTML( 'afterbegin', '<div style="position:absolute; top:200px; z-index: 200000000000000; width:500px; margin-left:-250px; left:50%; background-color:#fff; box-shadow: 0 19px 38px rgba(0,0,0,0.30), 0 15px 12px rgba(0,0,0,0.22); text-align:center; padding:50px;" id="listen-progress-container"></div>');
updateMessage("");
getPageCount();
