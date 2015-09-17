/** @jsx React.DOM */

var CONTAINER_ELEMENT_ID = "listens-viewer-container";
var container = document.getElementById(CONTAINER_ELEMENT_ID);

var ListensViewer = React.createClass({
    getInitialState: function () {
        return {
            userId: null,
            listens: null
        };
    },
    componentDidMount: function() {
        if (!container.dataset.userId) {
            console.error("ID of existing user needs to be specified" +
                          "in the data-user-id property.");
            return;
        }

        function getUrlParameter(sParam) {
            var sPageURL = decodeURIComponent(window.location.search.substring(1));
            var sURLVariables = sPageURL.split('&');
            for (var i = 0; i < sURLVariables.length; i++) {
                var sParameterName = sURLVariables[i].split('=');
                if (sParameterName[0] === sParam) {
                    return sParameterName[1] === undefined ? true : sParameterName[1];
                }
            }
        }

        var data_url = "/listen/user/" + container.dataset.userId;
        var minTimestamp = getUrlParameter("min-ts");
        if (minTimestamp) {
            data_url +=  "?min_ts=" + minTimestamp;
        }
        $.get(data_url,
            function(data) {
                if (this.isMounted()) {
                    this.setState({
                        userId: container.dataset.userId,
                        listens: data.payload.listens
                    });
                }
            }.bind(this)
        );
    },
    componentDidUpdate: function() {
        jQuery("abbr.timeago").timeago();
    },
    render: function () {
        if (this.state.listens) {
            var items = [];
            this.state.listens.forEach(function (listen) {
                items.push(<Listen
                    key={listen.listened_at}
                    metadata={listen.track_metadata}
                    timestamp={listen.listened_at}
                    />);
            }.bind(this));
            if (items.length > 0) {
                return (
                    <div>
                        <table className="table table-condensed table-striped">
                            <thead>
                            <tr>
                                <th>artist</th>
                                <th>track</th>
                                <th>time</th>
                            </tr>
                            </thead>
                            <tbody>{items}</tbody>
                        </table>
                        <ul className="pager">
                            <PreviousPageButton
                                userId={this.state.userId}
                                maxTimestamp={this.state.listens[0].listened_at + 1}
                                />
                            <NextPageButton
                                userId={this.state.userId}
                                minTimestamp={this.state.listens[this.state.listens.length-1].listened_at - 1}
                                />
                        </ul>
                    </div>
                );
            } else {
                return (<p className="text-muted">No listens.</p>);
            }

        } else {
            return <div>Loading listens...</div>;
        }
    }
});

var Listen = React.createClass({
    propTypes: {
        metadata: React.PropTypes.object.isRequired,
        timestamp: React.PropTypes.number.isRequired
    },
    render: function () {
        var timestamp = new Date(this.props.timestamp * 1000).toISOString();
        return (
            <tr>
                <td>{this.props.metadata.artist_name}</td>
                <td>{this.props.metadata.track_name}</td>
                <td><abbr className="timeago" title={timestamp}></abbr></td>
            </tr>
        );
    }
});

var PreviousPageButton = React.createClass({
    propTypes: {
        userId: React.PropTypes.string.isRequired,
        maxTimestamp: React.PropTypes.number.isRequired,
        onSwitch: React.PropTypes.func.isRequired
    },
    getInitialState: function () {
        return {
            enabled: false,
            minTimestamp: null
        };
    },
    componentDidMount: function() {
        $.get("/listen/user/" + container.dataset.userId +
              "?max_ts=" + this.props.maxTimestamp,
            function(data) {
                if (data.payload.count > 0) {
                    this.setState({
                        enabled: true,
                        minTimestamp: data.payload.listens[data.payload.listens.length - 1].listened_at - 1
                    });
                }
            }.bind(this)
        );
    },
    switchPage: function() {
        window.location.replace("/user/" + this.props.userId + "?min-ts=" + this.state.minTimestamp);
    },
    render: function () {
        if (this.state.enabled) {
            return <li className="previous">
                <a href="#" onClick={this.switchPage}>&larr; Previous</a>
            </li>;
        } else {
            return <li style={{display: 'none'}}></li>;
        }
    }
});

var NextPageButton = React.createClass({
    propTypes: {
        userId: React.PropTypes.string.isRequired,
        minTimestamp: React.PropTypes.number.isRequired,
        onSwitch: React.PropTypes.func.isRequired
    },
    getInitialState: function () {
        return {
            enabled: false
        };
    },
    componentDidMount: function() {
        $.get("/listen/user/" + container.dataset.userId +
              "?min_ts=" + this.props.minTimestamp,
            function(data) {
                this.setState({enabled: data.payload.count > 0});
            }.bind(this));
    },
    switchPage: function() {
        window.location.replace("/user/" + this.props.userId + "?min-ts=" + this.props.minTimestamp);
    },
    render: function () {
        if (this.state.enabled) {
            return <li className="next">
                <a href="#" onClick={this.switchPage}>Next &rarr;</a>
            </li>;
        } else {
            return <li style={{display: 'none'}}></li>;
        }
    }
});


React.render(<ListensViewer />, container);
