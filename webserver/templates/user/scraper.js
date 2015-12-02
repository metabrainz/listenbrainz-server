(function(){
    var numberOfPages = parseInt(document.getElementsByClassName("pages")[0].innerHTML.trim().split(" ")[3]);
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
                reportPageAndGetNext(this.response,page);
            } else if (/^5/.test(this.status)) {
                retry('got ' + this.status);
            } else {
                // ignore 40x
            }
        };
        xhr.ontimeout = function () {
            retry('timeout');
        };
        xhr.onabort = function () {
            // this should never happen
        };
        xhr.onerror = function () {
            retry('error');
        };
        xhr.send();
    }

    function reportPageAndGetNext(response,page){
        // format response
        var elem = document.createElement("div");
        elem.innerHTML = response;
        var struct = encodeScrobbles(elem);
        q.push(struct);
        if( page <= numberOfPages ){
            getLastFMPage(page+1);
        }
        else{
            // we've got our lastfm data
            q.done();
        }
    }

    function reportScrobbles(struct,completed) {
        if (!struct.payload.length) {
            return;
        }

        //must have a trailing slash
        var reportingURL = "{{ base_url }}";
        var xhr = new XMLHttpRequest();
        xhr.open("POST", reportingURL);
        xhr.setRequestHeader("Authorization", "Token {{ user_token }}");
        xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
        xhr.timeout = 10 * 1000; // 10 seconds
        xhr.onload = function(content) {
            if (xhr.status >= 200 && xhr.status < 300) {
                console.log("successfully reported page");
                completed(parseInt(xhr.getResponseHeader("X-RateLimit-Remaining")),parseInt(xhr.getResponseHeader("X-RateLimit-Reset")));
            } else if (xhr.status == 429) {
                console.log("received rate limit http error " + xhr.status + " req'ing");
            } else if (xhr.status >= 400 && xhr.status < 500) {
                // We mark 4xx errors as completed because we don't
                // retry them
                console.log("4xx error, skipping");
            } else if (xhr.status >= 500) {
                console.log("received http error " + xhr.status + " req'ing");
                reportScrobbles(struct);
            } else {
                console.log("received http status " + xhr.status + ", skipping");
            }
        };
        xhr.ontimeout = function(context) {
            console.log("timeout, req'ing");
            reportScrobbles(struct);
        };
        xhr.onabort = function(context) {
            console.log("abort, req'ing");
            reportScrobbles(struct);
        };
        xhr.onerror = function(context) {
            console.log("error, req'ing");
            reportScrobbles(struct);
        };
        xhr.send(JSON.stringify(struct));
    }

    var q = new ListenBrainzSubmissionQueue();
    q.on('update',function(count){
        updateMessage("<i class='fa fa-cog fa-spin'></i> Sending page " + count + " of " + numberOfPages + " to ListenBrainz<br><span style='font-size:8pt'>Please don't navigate while this is running</span>");
    });
    q.on('done',function(){
        updateMessage("<i class='fa fa-check'></i> Import finished<br><span style='font-size:8pt'>Thank you for using ListenBrainz</span>");
    });

    document.body.insertAdjacentHTML( 'afterbegin', '<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/font-awesome/4.4.0/css/font-awesome.min.css">');
    document.body.insertAdjacentHTML( 'afterbegin', '<div style="position:absolute; top:200px; z-index: 200000000000000; width:500px; margin-left:-250px; left:50%; background-color:#fff; box-shadow: 0 19px 38px rgba(0,0,0,0.30), 0 15px 12px rgba(0,0,0,0.22); text-align:center; padding:50px;" id="listen-progress-container"></div>');
    getLastFMPage(1);
    var version = "1.5";
    updateMessage('');

    function updateMessage(message) {
        document.getElementById("listen-progress-container").innerHTML =  "" +
            "<img src='{{ url_for('static', filename='img/listenbrainz-logo.svg', _external=True) }}' height='75'><br><br>" +
            message + "<br>" +
            "<br><span style='font-size:6pt; position:absolute; bottom:1px; right: 3px'>v"+version+"</span>";
    }

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
        var dateContainer = this.rootScrobbleElement.getElementsByClassName("chartlist-timestamp")[0];
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
                    function(elem) { return elem.getAttribute("href"); },
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

        };
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
        };

        return structure;
    }

    function ListenBrainzSubmissionQueue(){
        var self = this;
        self.remain = 1;
        self.timeout = 0;
        self.queue = [];
        self.processingReq = false;
        self.count = 0;
        self.doneSubmissions = false;
        self.start = true;

        self.eventHandlers = {};

        self.on = function(eventName, eventHandler){
            self.eventHandlers[eventName] = eventHandler;
        };

        self.push = function(struct){
            if(self.start){
                if (self.eventHandlers.update){
                    self.eventHandlers.update(1);
                }
                self.start = false;
            }
            self.queue.push(struct);
            if(!self.processingReq){
                self.processReq();
            }
        };

        self.done = function(){
            self.doneSubmissions = true;
        };

        self.processReq = function(){
            self.processingReq = true;
            struct = self.queue.pop();
            if(struct){
                self.remain--;
                setTimeout(function(){
                    if (self.eventHandlers.update){
                        self.eventHandlers.update(self.count);
                    }
                    reportScrobbles(struct,function(remain, reset){
                        self.processingReq = false;
                        self.count++;
                        self.remain = remain;
                        var current = new Date().getTime() / 1000;

                        if (self.remain)
                            self.timeout = Math.max(0, Math.ceil((reset - current) * 1000 / self.remain));
                        else
                            self.timeout = Math.max(0, Math.ceil((reset - current) * 1000));
                    });
                    self.processReq();
                },self.timeout);
            }
            else{
                if(self.doneSubmissions){
                    if (self.eventHandlers.done){
                        self.eventHandlers.done();
                    }
                }
            }
        };
      }
})();
