/** @jsx React.DOM */

var CONTAINER_ELEMENT_ID = "listens-viewer-container";
var container = document.getElementById(CONTAINER_ELEMENT_ID);

var ListensViewer = React.createClass({
    getInitialState: function () {
        return {
            listens: null
        };
    },
    componentDidMount: function() {
        if (!container.dataset.userId) {
            console.error("ID of existing user needs to be specified" +
                "in the data-user-id property.");
            return;
        }
        $.get("/listen/user/" + container.dataset.userId, function(data) {
            if (this.isMounted()) {
                this.setState({listens: data.payload.listens});
                console.log(this.state.listens);
            }
        }.bind(this));
    },
    componentDidUpdate: function() {
        jQuery("abbr.timeago").timeago();
    },
    render: function () {
        if (this.state.listens) {
            var items = [];
            this.state.listens.forEach(function (listen) {
                items.push(<Listen metadata={listen.track_metadata} timestamp={listen.listened_at} />);
            }.bind(this));
            if (items.length > 0) {
                return (
                    <table className="recordings table table-condensed table-hover">
                        <thead>
                        <tr>
                            <th>track</th>
                            <th>artist</th>
                            <th>time</th>
                        </tr>
                        </thead>
                        <tbody>{items}</tbody>
                    </table>
                );
            } else {
                return (<p className="text-muted">No listens.</p>);
            }

        } else {
            return <div>Loading your listens...</div>;
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
                <td>{this.props.metadata.track_name}</td>
                <td>{this.props.metadata.artist_name}</td>
                <td><abbr className="timeago" title={timestamp}></abbr></td>
            </tr>
        );
    }
});


React.render(<ListensViewer />, container);
