/** @jsx React.DOM */
/*
 This is a viewer for dataset evaluation jobs.

 Attribute "data-dataset-id" which references existing dataset by its ID need
 to be specified on container element.
 */

var CONTAINER_ELEMENT_ID = "eval-viewer-container";
var container = document.getElementById(CONTAINER_ELEMENT_ID);

var SECTION_JOB_LIST = "dataset_details";
var SECTION_JOB_DETAILS = "class_details";

// See database code for more info about these.
var JOB_STATUS_PENDING = "pending";
var JOB_STATUS_RUNNING = "running";
var JOB_STATUS_FAILED = "failed";
var JOB_STATUS_DONE = "done";


var EvaluationJobsViewer = React.createClass({
    getInitialState: function () {
        return {
            active_section: SECTION_JOB_LIST,
            jobs: null
        };
    },
    componentDidMount: function() {
        // Do not confuse property called "dataset" with our own datasets. See
        // https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/dataset
        // for more info about it.
        if (!container.dataset.datasetId) {
            console.error("ID of existing dataset needs to be specified" +
                "in data-dataset-id property.");
            return;
        }
        $.get("/datasets/" + container.dataset.datasetId + "/evaluation/json", function(data) {
            if (this.isMounted()) {
                this.setState({jobs: data.jobs});
                this.handleHashChange();
            }
        }.bind(this));

        // Hash is used to store ID of the job that is currently viewed.
        window.addEventListener('hashchange', this.handleHashChange);
    },
    componentWillUnmount: function() {
        window.removeEventListener('hashchange', this.handleHashChange);
    },
    handleHashChange: function(e) {
        // Hash is used to store ID of the currently viewed job.
        if (this.state.jobs) {
            var hash = window.location.hash.substr(1);
            var active_section = SECTION_JOB_LIST;
            if (hash.length > 0) {
                active_section = SECTION_JOB_DETAILS;
                for (var i = 0; i < this.state.jobs.length; ++i) {
                    if (this.state.jobs[i].id == hash) {
                        this.handleViewDetails(i);
                        console.debug(
                            "Found job with a specified ID (" + hash + "). " +
                            "Switching view."
                        );
                        return;
                    }
                }
                console.debug(
                    "Couldn't find any job with a specified ID (" + hash + "). " +
                    "Resetting to job list."
                );
                this.handleReturn();
            } else {
                this.handleReturn();
            }
        }
    },
    handleViewDetails: function (index) {
        this.setState({
            active_section: SECTION_JOB_DETAILS,
            active_job_index: index
        });
        window.location.hash = "#" + this.state.jobs[index].id;
    },
    handleReturn: function () {
        this.setState({
            active_section: SECTION_JOB_LIST,
            active_job_index: undefined
        });
        window.location.hash = "";
    },
    render: function () {
        if (this.state.jobs) {
            if (this.state.active_section == SECTION_JOB_LIST) {
                return (
                    <JobList
                        jobs={this.state.jobs}
                        onViewDetails={this.handleViewDetails} />
                );
            } else { // SECTION_JOB_DETAILS
                var active_job = this.state.jobs[this.state.active_job_index];
                return (
                    <JobDetails
                        id={active_job.id}
                        created={active_job.created}
                        updated={active_job.updated}
                        status={active_job.status}
                        statusMsg={active_job.status_msg}
                        result={active_job.result}
                        onReturn={this.handleReturn} />
                );
            }
        } else {
            return (<strong>Loading job list...</strong>);
        }
    }
});


// Classes used with SECTION_JOB_LIST:

var JobList = React.createClass({
    propTypes: {
        jobs: React.PropTypes.array.isRequired,
        onViewDetails: React.PropTypes.func.isRequired
    },
    render: function () {
        if (this.props.jobs.length > 0) {
            var items = [];
            this.props.jobs.forEach(function (cls, index) {
                items.push(
                    <JobRow
                        index={index}
                        id={cls.id}
                        created={cls.created}
                        status={cls.status}
                        onViewDetails={this.props.onViewDetails} />
                );
            }.bind(this));
            return (
                <table className="table table-hover job-list">
                    <thead>
                    <tr>
                        <th>Job ID</th>
                        <th>Status</th>
                        <th>Creation time</th>
                    </tr>
                    </thead>
                    <tbody>{items}</tbody>
                </table>
            );
        } else {
            return (
                <div className="alert alert-info">
                    This dataset has not been evaluated yet.
                </div>
            );
        }
    }
});

var JobRow = React.createClass({
    propTypes: {
        index: React.PropTypes.number.isRequired,
        id: React.PropTypes.string.isRequired,
        created: React.PropTypes.string.isRequired,
        status: React.PropTypes.string.isRequired,
        onViewDetails: React.PropTypes.func.isRequired
    },
    handleViewDetails: function (event) {
        event.preventDefault();
        this.props.onViewDetails(this.props.index);
    },
    render: function () {
        var status = "";
        switch (this.props.status) {
            case JOB_STATUS_PENDING:
                status = <span className="label label-info">In queue</span>;
                break;
            case JOB_STATUS_RUNNING:
                status = <span className="label label-primary">Running</span>;
                break;
            case JOB_STATUS_FAILED:
                status = <span className="label label-danger">Failed</span>;
                break;
            case JOB_STATUS_DONE:
                status = <span className="label label-success">Done</span>;
                break;
        }
        return (
            <tr className="job">
                <td className="id"><a href="#" onClick={this.handleViewDetails}>{this.props.id}</a></td>
                <td className="status">{status}</td>
                <td className="created">{this.props.created}</td>
            </tr>
        );
    }
});


// Classes used with SECTION_JOB_DETAILS:

var JobDetails = React.createClass({
    propTypes: {
        id: React.PropTypes.string.isRequired,
        created: React.PropTypes.string.isRequired,
        updated: React.PropTypes.string.isRequired,
        status: React.PropTypes.string.isRequired,
        statusMsg: React.PropTypes.string,
        result: React.PropTypes.object,
        onReturn: React.PropTypes.func.isRequired
    },
    render: function () {
        var status = "";
        switch (this.props.status) {
            case JOB_STATUS_PENDING:
                status = <div className="alert alert-info">
                    This job is in evaluation queue.
                </div>;
                break;
            case JOB_STATUS_RUNNING:
                status = <div className="alert alert-primary">
                    This evaluation job is being processed right now.
                </div>;
                break;
            case JOB_STATUS_FAILED:
                var errorMsg = "";
                if (this.props.statusMsg) {
                    errorMsg = <p>
                        Error details:<br />
                        {this.props.statusMsg}
                    </p>
                }
                status = <div className="alert alert-danger">
                    <strong>This evaluation job has failed!</strong>
                    {errorMsg}
                </div>;
                break;
            case JOB_STATUS_DONE:
                status = <div className="alert alert-success">
                    This evaluation job has been completed on {this.props.updated}.
                    You can find results below.
                </div>;
                break;
        }
        var header = <div>
            <h3>Job {this.props.id}</h3>
            <p>
                <a href='#' onClick={this.props.onReturn}>
                    <strong>&larr; Back to job list</strong>
                </a>
            </p>
            <p><strong>Creation time:</strong> {this.props.created}</p>
            {status}
        </div>;
        if (this.props.status === JOB_STATUS_DONE) {
            return <div className="job-details">
                {header}
                <Results
                    accuracy={this.props.result.accuracy}
                    table={this.props.result.table}
                    />
            </div>;
        } else {
            return <div>{header}</div>;
        }
    }
});

var Results = React.createClass({
    propTypes: {
        accuracy: React.PropTypes.number.isRequired,
        table: React.PropTypes.string.isRequired
    },
    render: function () {
        var classes = [];
        this.props.table.classes.forEach(function (cls) {
            classes.push(<th className="active">{cls}</th>);
        }.bind(this));
        var header = <tr>
            <th></th>
            {classes}
            <th></th>
            <th className="active">Proportion</th>
        </tr>;

        var rows = [];
        var so = this;
        this.props.table.rows.forEach(function (cls, index) {
            var predicted = [];
            cls.predicted.forEach(function (inner_cls, inner_index) {
                var className = "";
                if (inner_index == index) {
                    if (inner_cls.percentage > 0) { className = "success"; }
                } else {
                    if (inner_cls.percentage >= 10) { className = "danger"; }
                }
                predicted.push(
                    <td className={className}>{inner_cls.percentage.toFixed(2)}</td>
                );
            }.bind(so));
            rows.push(
                <tr>
                    <th className="active">{so.props.table.classes[index]}</th>
                    {predicted}
                    <th className="active">{so.props.table.classes[index]}</th>
                    <td>{cls.proportion.toFixed(2)}</td>
                </tr>
            );
        }.bind(this));

        var table = <table className="table table-bordered table-condensed table-inner">
            <tbody>{header}{rows}</tbody>
        </table>;

        return (
            <div className="results">
                <p><strong>Accuracy:</strong> {this.props.accuracy}%</p>
                <table className="table table-bordered">
                    <tbody>
                    <tr><th className="active">Predicted (%)</th></tr>
                    <tr>
                        <td>{table}</td>
                        <th className="active">Actual (%)</th>
                    </tr>
                    </tbody>
                </table>
            </div>
        );

    }
});


React.render(<EvaluationJobsViewer />, container);
