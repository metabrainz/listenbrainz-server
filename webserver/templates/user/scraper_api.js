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
    var loveButtonURL = this.rootScrobbleElement['url'];
    return extractlastFMIDFromURL(loveButtonURL);
};

Scrobble.prototype.artistName = function () {
    var artistName = this.rootScrobbleElement['artist']['#text'];
    return artistName;
};

Scrobble.prototype.trackName = function () {
    var trackData = this.rootScrobbleElement['name'];
    return trackData;
};

Scrobble.prototype.scrobbledAt = function () {
    var date = this.rootScrobbleElement['date']['uts'];
    return date;
};

Scrobble.prototype.optionalSpotifyID = function () {
    return select(
            isSpotifyURI,
            map(
                function(elem) { return elem.getAttribute("href") },
                this.rootScrobbleElement.getElementsByTagName("a")
               )
            )[0];
};

Scrobble.prototype.asJSONSerializable = function () {
    return {
        "track_metadata": {
            "track_name": this.trackName(),
            "artist_name": this.artistName(),
        },
        "listened_at": this.scrobbledAt()

    }
};

function extractlastFMIDFromURL(loveButtonURL) {
    var parts = loveButtonURL.split("/");
    return parts.slice(0, parts.length-2).join("/");
}

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
    xhr = null;
}

var version = "1.4";
var page = 1;
var numberOfPages = 1;
if (document.querySelector('.pages') != null) {
   numberOfPages = parseInt(document.getElementsByClassName("pages")[0].innerHTML.trim().split(" ")[3]);
}

var toReport = [];
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
    var url = "http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user={{ lastfm_username }}&api_key={{ lastfm_api_key }}&format=json&page=" + page;

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
            getCountAgain('got ' + this.status);
        } else {
            // ignore 40x
            getNextPagesIfSlots();
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
    xhr = null;
}

function reportScrobbles(struct) {
    if (!struct.payload.length) {
        pageDone();
        return;
    }

    timesReportScrobbles++;
    //must have a trailing slash
    var reportingURL = "{{ base_url }}" + "/";
    var xhr = new XMLHttpRequest();
    xhr.open("POST", reportingURL);
    xhr.setRequestHeader("Authorization", "Token {{ user_token }}");
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    xhr.timeout = 10 * 1000; // 10 seconds
    xhr.onload = function(content) {
        if (this.status >= 200 && this.status < 300) {
            console.log("successfully reported page");
            pageDone();
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
    delete(xhr);
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
        updateMessage("<i class='fa fa-cog fa-spin'></i> working<br><span style='font-size:8pt'>Please don't navigate away from this page while the process is running</span>");
    }
    var struct = encodeScrobbles(response);
    reportScrobbles(struct);
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
