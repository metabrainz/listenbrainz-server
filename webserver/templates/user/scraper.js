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
    var loveButtonForm = this.rootScrobbleElement.getElementsByTagName("form")[0];
    var loveButtonURL = loveButtonForm.getAttribute("action");
    return extractlastFMIDFromLoveButtonURL(loveButtonURL);
};

Scrobble.prototype.artistName = function () {
    var artistElement = this.rootScrobbleElement.getElementsByClassName("chartlist-artists")[0];
    artistElement = artistElement.children[0];
    var artistName = artistElement.textContent || artistElement.innerText;
    return artistName;
};

Scrobble.prototype.trackName = function () {
    var trackElement = this.rootScrobbleElement.getElementsByClassName("link-block-target")[0];
    return trackElement.textContent || trackElement.innerText;
};

Scrobble.prototype.scrobbledAt = function () {
    var dateContainer = this.rootScrobbleElement.getElementsByClassName("chartlist-timestamp")[0]
    if (!dateContainer) {
        return 0;
    }
    var dateElement = dateContainer.getElementsByTagName("span")[0];
    var dateString = dateElement.getAttribute("title");
    //we have to do this because javascript's date parse method doesn't
    //directly accept lastfm's new date format but it does if we add the
    //space before am or pm
    var manipulatedDateString = dateString.replace("am", " am").replace("pm", " pm") + " UTC";
    return Math.round(Date.parse(manipulatedDateString)/1000);
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
            "additional_info" : {
                 "spotify_id": this.optionalSpotifyID()
            },
        },
        "listened_at": this.scrobbledAt()

    }
};

function extractlastFMIDFromLoveButtonURL(loveButtonURL) {
    var parts = loveButtonURL.split("/");
    return parts.slice(0, parts.length-1).join("/");
}

function encodeScrobbles(root) {
    var scrobbles = root.getElementsByClassName("js-link-block");
    var parsedScrobbles = map(function(rawScrobble) {
        var scrobble = new Scrobble(rawScrobble);
        return scrobble.asJSONSerializable();
    }, scrobbles);

    var structure = {
        "listen_type" : "import",
        "payload"     : parsedScrobbles
    }

    return structure;
}

function getLastFMPage(page) {
    function retry(reason) {
        console.warn(reason + ' fetching last.fm page=' + page + ', retrying in 3s');
        setTimeout(function () {
            getLastFMPage(page);
        }, 3000);
    }

    var xhr = new XMLHttpRequest();
    xhr.timeout = 10 * 1000; // 10 seconds
    xhr.open("GET", encodeURI("http://www.last.fm/user/{{ lastfm_username }}/library?page=" + page + "&_pjax=%23content"));
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

var version = "1.5";
var page = 1;
var numberOfPages = 1;
var pages = document.getElementsByClassName("pages");
if (pages.length > 0) {
    numberOfPages = parseInt(pages[0].innerHTML.trim().split(" ")[3]);
}

var numCompleted = 0;
var maxActiveFetches = 10;
var activeFetches = 0;

var submitQueue = [];
var isSubmitActive = false;
var rl_remain = -1;
var rl_reset = -1;

var timesReportScrobbles = 0;
var timesGetPage = 0;
var times4Error = 0;
var times5Error = 0;


function reportPageAndGetNext(response) {
    timesGetPage++;
    if (page == 1) {
        updateMessage("<i class='fa fa-cog fa-spin'></i> working<br><span style='font-size:8pt'>Please don't navigate away from this page while the process is running</span>");
    }
    var elem = document.createElement("div");
    elem.innerHTML = response;

    var struct = encodeScrobbles(elem);
    submitQueue.push(struct);
    if (!isSubmitActive)
    {
        isSubmitActive = true;
        submitListens();
    }

    getNextPagesIfSlots();
}

function getNextPagesIfSlots() {
    // Get a new lastfm page and queue it only if there are more pages to download and we have
    // less than 10 pages waiting to submit
    while (page <= numberOfPages && activeFetches < maxActiveFetches) {
        activeFetches++;
        getLastFMPage(page);
        page += 1;
    }
}

function pageDone() {
    activeFetches--;
    numCompleted++;

    // start the next submission
    if (submitQueue.length)
        submitListens();
    else
        isSubmitActive = false;

    // Check to see if we need to start up more fetches
    getNextPagesIfSlots();
}


function submitListens() {

    struct = submitQueue.shift()
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
            //must have a trailing slash
            var reportingURL = "{{ base_url }}";
            var xhr = new XMLHttpRequest();
            xhr.open("POST", reportingURL);
            xhr.setRequestHeader("Authorization", "Token {{ user_token }}");
            xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
            xhr.timeout = 10 * 1000; // 10 seconds
            xhr.onload = function(content) {
                rl_remain = parseInt(xhr.getResponseHeader("X-RateLimit-Remaining"));
                rl_reset = parseInt(xhr.getResponseHeader("X-RateLimit-Reset"));
                if (this.status >= 200 && this.status < 300) {
                    pageDone();
                } else if (this.status == 429) {
                    // This should never happen, but if it does, toss it back in and try again.
                    submitQueue.unshift();
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

                    // If something causes a 500 error, better not repeat it and just skip it.
                    pageDone();
                } else {
                    console.log("received http status " + this.status + ", skipping");
                    pageDone();
                }
                if (numCompleted >= numberOfPages) {
                    updateMessage("<i class='fa fa-check'></i> Import finished<br><span><a href='https://listenbrainz.org/user/{{user_id}}'>Go to your ListenBrainz profile</a> | <a href='' id='close-progress-container'>Close</a></span><br><span style='font-size:8pt'>Thank you for using ListenBrainz</span>");
                    var close = document.getElementById('close-progress-container');
                    close.addEventListener('click', function(ev) {
                        ev.preventDefault();
                        var el = document.getElementById('listen-progress-container');
                        el.parentNode.removeChild(el);
                    }, false);
                } else {
                    updateMessage("<i class='fa fa-cog fa-spin'></i> Sending page " + numCompleted + " of " + numberOfPages + " to ListenBrainz<br><span style='font-size:8pt'>Please don't navigate while this is running</span>");
                }
            };
            xhr.ontimeout = function(context) {
                console.log("timeout, req'ing");
                submitListens(struct);
            }
            xhr.onabort = function(context) {
                console.log("abort, req'ing");
                submitListens(struct);
            };
            xhr.onerror = function(context) {
                console.log("error, req'ing");
                submitListens(struct);
            };
            xhr.send(JSON.stringify(struct));
        }, delay);
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
getNextPagesIfSlots();
