
/*
 * listenbrainz-server - Server for the ListenBrainz project.
 *
 * Copyright (C) 2017 MetaBrainz Foundation Inc.
 * Copyright (C) 2017 Param Singh
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
 */

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
      var result = applicable(collection[i]);
      if ('listened_at' in result) {
        // If there is no 'listened_at' attribute then either the listen is invalid or the
        // listen is currently playing. In both cases we need to skip the submission.
        newCollection.push(result);
      };
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

Scrobble.prototype.releaseName = function() {
    if ('album' in this.rootScrobbleElement && '#text' in this.rootScrobbleElement['album']) {
        return this.rootScrobbleElement['album']['#text'];
    } else {
        return "";
    }
};

Scrobble.prototype.scrobbledAt = function () {
    if ('date' in this.rootScrobbleElement && 'uts' in this.rootScrobbleElement['date']) {
        return this.rootScrobbleElement['date']['uts'];
    } else {
        /*
        The audioscrobbler API's output differs when the user is playing song.
        In case, when the user is playing song, the API returns 1st listen with
        attribute as {"@attr": {"now_playing":"true"}} while other listens with
        attribute as {"date": {"utc":"12345756", "#text":"21 Jul 2016, 10:22"}}
        We need to only submit listens which were played in the past.
        */
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
            "release_name": this.releaseName(),
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

    var url = "{{ lastfm_api_url }}?method=user.getrecenttracks&user={{ lastfm_username }}&api_key={{ lastfm_api_key }}&format=json&page=" + page;

    var xhr = new XMLHttpRequest();
    xhr.timeout = 10 * 1000; // 10 seconds
    xhr.open("GET", encodeURI(url));
    xhr.onload = function () {
        if (/^2/.test(this.status)) {
            if (numberOfPages <= 1) {
                var data = JSON.parse(this.response);
                numberOfPages = data['recenttracks']['@attr']['totalPages'];

                // initially set the stop page to the total number of pages
                // we'll later update it if we're able to stop earlier because of previous imports
                stopPage = numberOfPages;

                if (data['recenttracks']['track'].length > 0) {
                    // if date is present, use it
                    if ('date' in data['recenttracks']['track'][0]) {
                        maximumTimestampForImport = data['recenttracks']['track'][0]['date']['uts'];
                    }
                    else { // the latest listen is a playing_now, use current time
                        maximumTimestampForImport = Math.floor(Date.now() / 1000);
                    }
                }
            }
            reportPageAndGetNext(this.response, page);
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

var user_name = "{{ user_name }}";
var version = "1.7.1";
var page = 1;
var numberOfPages = 1;
var playCount = -1; // the number of scrobbles reported by Last.FM
var countReceived = 0; // number of scrobbles the Last.FM API sends us, this can be diff from playCount
var stopPage = numberOfPages; // the page that the import stops at

var numCompleted = 0;
var maxActiveFetches = 10;
var activeFetches = 0;

var submitQueue = [];
var isSubmitActive = false;
var rl_remain = -1;
var rl_reset = -1;
var rl_origin = -1;

var timesReportScrobbles = 0;
var timesGetPage = 0;
var times4Error = 0;
var times5Error = 0;

// a flag that is set to true once we get to pages that we've done already in previous imports
var previouslyDone = false;

// the latest timestamp that we've imported earlier, so that we know where to stop
var latestImportTime = 0;

// the latest listen found in this import, we'll report back to the server with this
var maximumTimestampForImport = 0;

var incrementalImport = false;

function reportPageAndGetNext(response, page) {
    timesGetPage++;
    if (page == 1) {
        updateMessage("<i class='fa fa-cog fa-spin'></i> working<br><span style='font-size:8pt'>Please do not close this page while the process is running</span>");
    }
    var struct = encodeScrobbles(response);
    submitQueue.push(struct);
    countReceived += struct['payload'].length;
    if (!struct.payload.length) 
        pageDone();
    else{
        if (struct['payload'][struct['payload'].length - 1]['listened_at'] < latestImportTime) {
            previouslyDone = true;
            stopPage = page;
        }
        if (!isSubmitActive){
            isSubmitActive = true;
            submitListens();
        }
    }

    getNextPagesIfSlots();
}

function getNextPagesIfSlots() {
    // Get a new lastfm page and queue it only if there are more pages to download and we have
    // less than 10 pages waiting to submit
    while (!previouslyDone && page <= numberOfPages && activeFetches < maxActiveFetches) {
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

function getRateLimitDelay() {
    /* Get the amount of time we should wait according to LB rate limits before making a request to LB */
    var delay = 0;
    var current = new Date().getTime() / 1000;
    if (rl_reset < 0 || current > rl_origin + rl_reset)
        delay = 0;
    else if (rl_remain > 0)
        delay = Math.max(0, Math.ceil((rl_reset * 1000) / rl_remain));
    else
        delay = Math.max(0, Math.ceil(rl_reset * 1000));
    return delay;
}

function updateRateLimitParameters(xhr) {
    /* Update the variables we use to honor LB's rate limits */
    rl_remain = parseInt(xhr.getResponseHeader("X-RateLimit-Remaining"));
    rl_reset = parseInt(xhr.getResponseHeader("X-RateLimit-Reset-In"));
    rl_origin = new Date().getTime() / 1000;
}

function submitListens() {

    struct = submitQueue.shift()

    var delay = getRateLimitDelay();

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
                updateRateLimitParameters(xhr);
                if (this.status >= 200 && this.status < 300) {
                    pageDone();
                } else if (this.status == 429) {
                    // This should never happen, but if it does, toss it back in and try again.
                    submitQueue.unshift(struct);
                    submitListens();
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
                if (numCompleted >= stopPage) {
                    updateLatestImportTimeOnLB();

                } else {
                    var msg = "<i class='fa fa-cog fa-spin'></i> Sending page " + numCompleted;

                    // show total number of pages if this is the first import and not an incremental
                    // import
                    if (!incrementalImport) {
                        msg += " of " + numberOfPages;
                    }

                    msg += " to ListenBrainz.<br><span style='font-size:8pt'>";

                    // show a message explaining that this is an incremental import
                    if (incrementalImport) {
                        msg += "Note: This import will stop at the starting point of your last import. :)<br>";
                    }

                    msg += "Please don't close this page while this is running</span>"
                    updateMessage(msg);
                }
            };
            xhr.ontimeout = function(context) {
                console.log("timeout, req'ing");
                submitQueue.unshift(struct);
                submitListens();
            }
            xhr.onabort = function(context) {
                console.log("abort, req'ing");
                submitQueue.unshift(struct);
                submitListens();
            };
            xhr.onerror = function(context) {
                console.log("error, req'ing");
                submitQueue.unshift(struct);
                submitListens();
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

function getLatestImportTime() {
    /*
     *  Send a GET request to the ListenBrainz server to get the latest import time
     *  from previous imports for the user.
     */

    var delay = getRateLimitDelay();
    setTimeout(function() {
        // user_name has already been uri encoded on the server
        var url = "{{ import_url }}?user_name=" + user_name;

        var xhr = new XMLHttpRequest();
        xhr.open("GET", url);
        xhr.onload = function(content) {
            updateRateLimitParameters(xhr);
            if (this.status == 200) {
                latestImportTime = parseInt(JSON.parse(this.response)['latest_import']);

                // if the latest import time is greater than 0, this is an incremental import
                // and messages should be shown accordingly
                incrementalImport = latestImportTime > 0;

                getNextPagesIfSlots();
            }
            else {
                updateMessage("An error occured while trying to import from Last.fm, please try again. :(");
            }
        };
        xhr.send();
    }, delay);
}

function updateLatestImportTimeOnLB() {
    /*
     * Send a POST request to the ListenBrainz server after the import is complete to
     * update the latest import time on the server. This will make future imports stop
     * when they reach this point of time in the listen history.
     */

    var delay = getRateLimitDelay();
    setTimeout(function() {
        var url = "{{ import_url }}";
        var xhr = new XMLHttpRequest();
        xhr.open("POST", url);
        xhr.setRequestHeader("Authorization", "Token {{ user_token }}");
        xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
        xhr.timeout = 10 * 1000; // 10 seconds
        xhr.onload = function(content) {
            updateRateLimitParameters(xhr);
            if (this.status == 200) {
                var final_msg = "<i class='fa fa-check'></i> Import finished<br>";
                final_msg += "<span><a href={{ profile_url }}>Close and go to your ListenBrainz profile</a></span><br>";
                final_msg += "<span style='font-size:8pt'>Successfully submitted " + countReceived + " listens to ListenBrainz."
                    + " Please note that some of these listens might be duplicates leading to a lower listen count on ListenBrainz.</span></br>";

                // if the count received is different from the api count, show a message accordingly
                // also don't show this message if it's an incremental import, because countReceived
                // and playCount will be different by definition in incremental imports
                if (!incrementalImport && playCount != -1 && countReceived != playCount) {
                    final_msg += "<em><span style='font-size:10pt;' class='text-danger'>The number of submitted listens is different from the "
                        + playCount + " that Last.fm reports due to an inconsistency in their API, sorry!</span></em><br>";
                }

                final_msg += "<span style='font-size:8pt'>Thank you for using ListenBrainz!</span>";
                updateMessage(final_msg);
            }
            else {
                updateMessage("An error occurred, please try again. :(");
            }
        };
        xhr.send(JSON.stringify({
            'ts': maximumTimestampForImport
        }));
    }, delay);
}

function getTotalNumberOfScrobbles() {
    /*
     * Get the total play count reported by Last.FM for user
     */

    function retry() {
        setTimeout(getTotalNumberOfScrobbles, 3000);
    }

    var url = '{{ lastfm_api_url }}?method=user.getinfo&user={{ lastfm_username }}&api_key={{ lastfm_api_key }}&format=json';

    var xhr = new XMLHttpRequest();
    xhr.timeout = 10 * 1000; // 10 seconds
    xhr.open('GET', encodeURI(url));
    xhr.onload = function () {
        var data = JSON.parse(this.response)['user'];
        if ('playcount' in data) {
            playCount = parseInt(data['playcount']);
        }
        else {
            playCount = -1;
        }
    };
    xhr.ontimeout = function () {
        retry();
    };
    xhr.onerror = function () {
        retry();
    };
    xhr.send();
}

document.body.insertAdjacentHTML( 'afterbegin', '<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/font-awesome/4.4.0/css/font-awesome.min.css">');
document.body.insertAdjacentHTML( 'afterbegin', '<div style="position:fixed; top:200px; z-index: 200000000000000; width:500px; margin-left:-250px; left:50%; background-color:#fff; box-shadow: 0 19px 38px rgba(0,0,0,0.30), 0 15px 12px rgba(0,0,0,0.22); text-align:center; padding:50px;" id="listen-progress-container"></div>');
updateMessage("Your import from Last.fm is starting!");
getTotalNumberOfScrobbles();
getLatestImportTime();