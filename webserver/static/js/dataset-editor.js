/** @jsx React.DOM */
/*
 This is a dataset editor. It works in two modes:
 - create (creates new dataset from scratch)
 - edit (edits existing dataset)

 Mode is set by defining "data-mode" attribute on the container element which is
 referenced in CONTAINER_ELEMENT_ID. Value of this attribute is either "create"
 or "edit" (see definitions below: MODE_CREATE and MODE_EDIT).

 When mode is set to "edit", attribute "data-edit-id" need to be specified. This
 attribute references existing dataset by its ID. When Dataset component is
 mounted, it pull existing dataset for editing from the server.
 */

var CONTAINER_ELEMENT_ID = "dataset-editor";
var container = document.getElementById(CONTAINER_ELEMENT_ID);

var MODE_CREATE = "create";
var MODE_EDIT = "edit";

var SECTION_DATASET_DETAILS = "dataset_details";
var SECTION_CLASS_DETAILS = "class_details";

/*
 Dataset is the primary class in the dataset editor. Its state contains
 dataset itself and other internal variables:
   - mode (determines what mode dataset editor is in; can be either MODE_CREATE
     when creating new dataset or MODE_EDIT when modifying existing dataset)
   - data:
     - id (dataset ID that is used only when editing existing dataset)
     - name (name of the dataset)
     - description (optional description of the dataset)
     - classes: [ (array of classes with the following structure)
       - name
       - description
       - recordings (array of recording MBIDs)
     ]
   - active_section (determines what major part of the UI is currently shown
     to a user)

 It is divided into two sections (current section is set in active_section):
   - SECTION_DATASET_DETAILS (editing dataset info and list of classes)
   - SECTION_CLASS_DETAILS (editing specific class; this also requires
     active_class_index variable to be set in Dataset state)
 */
var Dataset = React.createClass({
    getInitialState: function () {
        return {
            mode: container.dataset.mode,
            active_section: SECTION_DATASET_DETAILS,
            data: null
        };
    },
    componentDidMount: function() {
        // This function is invoked when Dataset component is originally
        // mounted. Here we need to check what mode dataset editor is in, and
        // pull data from the server if mode is MODE_EDIT.
        // Do not confuse property called "dataset" with our own datasets. See
        // https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/dataset
        // for more info about it.
        if (this.state.mode == MODE_EDIT) {
            if (!container.dataset.editId) {
                console.error("ID of existing dataset needs to be specified" +
                "in data-edit-id property.");
                return;
            }
            $.get("/datasets/" + container.dataset.editId + "/json", function(result) {
                if (this.isMounted()) { this.setState({data: result}); }
            }.bind(this));
        } else {
            if (this.state.mode != MODE_CREATE) {
                console.warn('Unknown dataset editor mode! Using default: MODE_CREATE.');
            }
            this.setState({
                mode: MODE_CREATE,
                data: {
                    name: "",
                    description: "",
                    classes: [],
                    public: true
                }
            });
        }
    },
    handleDetailsUpdate: function (name, description) {
        var nextStateData = this.state.data;
        nextStateData.name = name;
        nextStateData.description = description;
        this.setState({data: nextStateData});
    },
    handlePrivacyUpdate: function () {
        var nextStateData = this.state.data;
        nextStateData.public = this.refs.public.getDOMNode().checked;
        this.setState({data: nextStateData});
    },
    handleReturn: function () {
        this.setState({
            active_section: SECTION_DATASET_DETAILS,
            active_class_index: undefined
        });
    },
    handleClassCreate: function () {
        var nextStateData = this.state.data;
        nextStateData.classes.push({
            name: "",
            description: "",
            recordings: []
        });
        this.setState({data: nextStateData});
    },
    handleClassEdit: function (index) {
        this.setState({
            active_section: SECTION_CLASS_DETAILS,
            active_class_index: index
        });
    },
    handleClassDelete: function (index) {
        var data = this.state.data;
        data.classes.splice(index, 1);
        this.setState({data: data});
    },
    handleClassUpdate: function (index, name, description, recordings) {
        var data = this.state.data;
        data.classes[index].name = name;
        data.classes[index].description = description;
        data.classes[index].recordings = recordings;
        this.setState({data: data});
    },
    render: function () {
        if (this.state.data) {
            if (this.state.active_section == SECTION_DATASET_DETAILS) {
                // TODO: Move ClassList into DatasetDetails
                return (
                    <div>
                        <DatasetDetails
                            name={this.state.data.name}
                            description={this.state.data.description}
                            onDetailsUpdate={this.handleDetailsUpdate} />
                        <ClassList
                            classes={this.state.data.classes}
                            onClassCreate={this.handleClassCreate}
                            onClassEdit={this.handleClassEdit}
                            onClassDelete={this.handleClassDelete} />
                        <hr />
                        <p class="checkbox">
                            <label>
                                <input
                                    ref="public"
                                    type="checkbox"
                                    checked={this.state.data.public}
                                    onChange={this.handlePrivacyUpdate} />
                                &nbsp;<strong>Make this dataset public</strong>
                            </label>
                        </p>
                        <SubmitDatasetButton
                            mode={this.state.mode}
                            data={this.state.data} />
                    </div>
                );
            } else { // SECTION_CLASS_DETAILS
                var active_class = this.state.data.classes[this.state.active_class_index];
                return (
                    <ClassDetails
                        id={this.state.active_class_index}
                        name={active_class.name}
                        description={active_class.description}
                        recordings={active_class.recordings}
                        datasetName={this.state.data.name}
                        onReturn={this.handleReturn}
                        onClassUpdate={this.handleClassUpdate} />
                );
            }
        } else {
            return (<strong>Loading...</strong>);
        }
    }
});


// Classes used with SECTION_DATASET_DETAILS:

var DatasetDetails = React.createClass({
    propTypes: {
        name: React.PropTypes.string.isRequired,
        description: React.PropTypes.string.isRequired,
        onDetailsUpdate: React.PropTypes.func.isRequired
    },
    handleDetailsUpdate: function () {
        this.props.onDetailsUpdate(
            this.refs.name.getDOMNode().value,
            this.refs.description.getDOMNode().value
        );
    },
    render: function () {
        return (
            <div className="dataset-details">
                <h3>
                    <input type="text"
                           placeholder="Name" required="required"
                           value={this.props.name} ref="name"
                           size={this.props.name.length}
                           onChange={this.handleDetailsUpdate} />
                </h3>
                <textarea ref="description"
                          placeholder="Description (optional)"
                          value={this.props.description}
                          onChange={this.handleDetailsUpdate}></textarea>
            </div>
        );
    }
});

var SubmitDatasetButton = React.createClass({
    propTypes: {
        mode: React.PropTypes.string.isRequired,
        data: React.PropTypes.object.isRequired
    },
    handleSubmit: function (e) {
        e.preventDefault();
        this.setState({
            enabled: false,
            errorMsg: null
        });
        var submitEndpoint = null;
        if (this.props.mode == MODE_CREATE) {
            submitEndpoint = "/datasets/create";
        } else { // MODE_EDIT
            submitEndpoint = "/datasets/" + container.dataset.editId + "/edit";
        }
        var so = this;
        $.ajax({
            type: "POST",
            url: submitEndpoint,
            data: JSON.stringify({
                'id': this.props.data.id,  // used only with MODE_EDIT
                'name': this.props.data.name,
                'description': this.props.data.description,
                'classes': this.props.data.classes,
                'public': this.props.data.public
            }),
            dataType: "json",
            contentType: "application/json; charset=utf-8",
            success: function (data, textStatus, jqXHR) {
                window.location.replace("/datasets/" + data.dataset_id);
            },
            error: function (jqXHR, textStatus, errorThrown) {
                so.setState({
                    enabled: true,
                    errorMsg: jqXHR.responseJSON
                });
            }
        });
    },
    getInitialState: function () {
        return {
            enabled: true,
            errorMsg: null
        };
    },
    render: function () {
        var buttonText = "Submit";
        if (this.props.mode == MODE_EDIT) {
            buttonText = "Update";
        }
        return (
            <div className="form-group">
                <p className={this.state.errorMsg ? 'text-danger' : 'hidden'}>
                    <strong>Error occured while submitting this dataset:</strong>
                    <br />{ this.state.errorMsg }
                </p>
                <button onClick={this.handleSubmit} type="button"
                        disabled={this.state.enabled ? '' : 'disabled'}
                        className="btn btn-default btn-primary">{buttonText}</button>
            </div>
        );
    }
});

var ClassList = React.createClass({
    propTypes: {
        classes: React.PropTypes.array.isRequired,
        onClassCreate: React.PropTypes.func.isRequired,
        onClassEdit: React.PropTypes.func.isRequired,
        onClassDelete: React.PropTypes.func.isRequired
    },
    render: function () {
        var items = [];
        this.props.classes.forEach(function (cls, index) {
            items.push(<Class id={index}
                              name={cls.name}
                              description={cls.description}
                              recordingCounter={cls.recordings.length}
                              onClassEdit={this.props.onClassEdit}
                              onClassDelete={this.props.onClassDelete} />);
        }.bind(this));
        return (
            <div>
                <h4>Classes</h4>
                <div className="class-list row">
                    {items}
                    <div className="col-md-3 class">
                        <a className="thumbnail add-class-link" href='#'
                           onClick={this.props.onClassCreate}>
                            + Add new class
                        </a>
                    </div>
                </div>
            </div>
        );
    }
});

var Class = React.createClass({
    propTypes: {
        id: React.PropTypes.number.isRequired,
        name: React.PropTypes.string.isRequired,
        description: React.PropTypes.string.isRequired,
        recordingCounter: React.PropTypes.number.isRequired,
        onClassDelete: React.PropTypes.func.isRequired,
        onClassEdit: React.PropTypes.func.isRequired
    },
    handleDelete: function (event) {
        event.preventDefault();
        this.props.onClassDelete(this.props.id);
    },
    handleEdit: function (event) {
        event.preventDefault();
        this.props.onClassEdit(this.props.id);
    },
    render: function () {
        var name = this.props.name;
        if (!name) name = <em>Unnamed class #{this.props.id + 1}</em>;
        var recordingsCounterText = this.props.recordingCounter.toString() + " ";
        if (this.props.recordingCounter == 1) recordingsCounterText += "recording";
        else recordingsCounterText += "recordings";
        return (
            <div className="col-md-3 class">
                <a href="#" onClick={this.handleEdit} className="thumbnail">
                    <div className="name">{name}</div>
                    <div className="counter">{recordingsCounterText}</div>
                </a>
                <div className="controls clearfix">
                    <button type="button" className="close pull-right" title="Remove class"
                            onClick={this.handleDelete}>&times;</button>
                </div>
            </div>
        );
    }
});


// Classes used with SECTION_CLASS_DETAILS:

var ClassDetails = React.createClass({
    propTypes: {
        id: React.PropTypes.number.isRequired,
        name: React.PropTypes.string.isRequired,
        description: React.PropTypes.string.isRequired,
        recordings: React.PropTypes.array.isRequired,
        datasetName: React.PropTypes.string.isRequired,
        onReturn: React.PropTypes.func.isRequired,
        onClassUpdate: React.PropTypes.func.isRequired
    },
    handleClassUpdate: function() {
        this.props.onClassUpdate(
            this.props.id,
            this.refs.name.getDOMNode().value,
            this.refs.description.getDOMNode().value,
            this.props.recordings
        );
    },
    handleRecordingsUpdate: function (recordings) {
        this.props.onClassUpdate(
            this.props.id,
            this.props.name,
            this.props.description,
            recordings
        );
    },
    render: function () {
        return (
            <div className="class-details">
                <h3>
                    <a href='#' onClick={this.props.onReturn}
                       title="Back to dataset details">
                        {this.props.datasetName}
                    </a>
                    &nbsp;/&nbsp;
                    <input type="text" placeholder="Class name"
                           ref="name" required="required"
                           id="class-name"
                           onChange={this.handleClassUpdate}
                           size={this.props.name.length}
                           value={this.props.name} />
                </h3>
                <p>
                    <a href='#' onClick={this.props.onReturn}>
                        <strong>&larr; Back to class list</strong>
                    </a>
                </p>
                <textarea ref="description"
                          placeholder="Description of this class (optional)"
                          onChange={this.handleClassUpdate}
                          value={this.props.description}></textarea>
                <Recordings
                    recordings={this.props.recordings}
                    onRecordingsUpdate={this.handleRecordingsUpdate} />
            </div>
        );
    }
});

var Recordings = React.createClass({
    propTypes: {
        recordings: React.PropTypes.array.isRequired,
        onRecordingsUpdate: React.PropTypes.func.isRequired
    },
    handleRecordingSubmit: function (mbid) {
        var recordings = this.props.recordings;
        recordings.push(mbid);
        this.props.onRecordingsUpdate(recordings);
    },
    handleRecordingDelete: function (mbid) {
        var recordings = this.props.recordings;
        var index = recordings.indexOf(mbid);
        if (index > -1) {
            recordings.splice(index, 1);
        }
        this.props.onRecordingsUpdate(recordings);
    },
    render: function () {
        return (
            <div>
                <h4>Recordings</h4>
                <RecordingList
                    recordings={this.props.recordings}
                    onRecordingDelete={this.handleRecordingDelete} />
                <RecordingAddForm
                    recordings={this.props.recordings}
                    onRecordingSubmit={this.handleRecordingSubmit} />
            </div>
        );
    }
});

var RecordingAddForm = React.createClass({
    propTypes: {
        recordings: React.PropTypes.array.isRequired,
        onRecordingSubmit: React.PropTypes.func.isRequired
    },
    handleSubmit: function (event) {
        event.preventDefault();
        var mbid = this.refs.mbid.getDOMNode().value.trim();
        if (!mbid) {
            return;
        }
        this.props.onRecordingSubmit(mbid);
        this.refs.mbid.getDOMNode().value = '';
    },
    handleChange: function () {
        var mbid = this.refs.mbid.getDOMNode().value;
        var isValidUUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(mbid);
        var isNotDuplicate = this.props.recordings.indexOf(mbid) == -1;
        this.setState({validInput: (isValidUUID && isNotDuplicate) || mbid.length == 0});
        // TODO: Show informative error messages if input is invalid.
    },
    getInitialState: function () {
        return {validInput: true};
    },
    render: function () {
        return (
            <form className="recording-add clearfix form-inline form-group-sm" onSubmit={this.handleSubmit}>
                <div className={this.state.validInput ? 'input-group' : 'input-group has-error'}>
                    <input type="text" className="form-control input-sm" placeholder="MusicBrainz ID"
                           ref="mbid" onChange={this.handleChange} />
                    <span className="input-group-btn">
                        <button disabled={this.state.validInput ? '' : 'disabled'}
                                className="btn btn-default btn-sm" type="submit">Add recording</button>
                    </span>
                </div>
            </form>
        );
    }
});

var RecordingList = React.createClass({
    propTypes: {
        recordings: React.PropTypes.array.isRequired,
        onRecordingDelete: React.PropTypes.func.isRequired
    },
    render: function () {
        var items = [];
        this.props.recordings.forEach(function (recording) {
            items.push(<Recording key={recording} mbid={recording}
                                  onRecordingDelete={this.props.onRecordingDelete} />);
        }.bind(this));
        if (items.length > 0) {
            return (
                <table className="recordings table table-condensed table-hover">
                    <thead>
                    <tr>
                        <th>MusicBrainz ID</th>
                        <th>Recording</th>
                        <th></th>
                    </tr>
                    </thead>
                    <tbody>{items}</tbody>
                </table>
            );
        } else {
            return (<p className="text-muted">No recordings.</p>);
        }
    }
});

var RECORDING_STATUS_LOADING = 'loading'; // loading info from the server
var RECORDING_STATUS_ERROR = 'error';     // failed to load info about recording
var RECORDING_STATUS_LOADED = 'loaded';  // info has been loaded
var Recording = React.createClass({
    propTypes: {
        mbid: React.PropTypes.string.isRequired,
        onRecordingDelete: React.PropTypes.func.isRequired
    },
    getInitialState: function () {
        return {
            status: RECORDING_STATUS_LOADING
        };
    },
    componentDidMount: function () {
        $.ajax({
            type: "GET",
            url: "/datasets/recording/" + this.props.mbid,
            success: function (data) {
                this.setState({
                    details: data.recording,
                    status: RECORDING_STATUS_LOADED
                });
            }.bind(this),
            error: function () {
                this.setState({
                    error: "Recording not found!",
                    status: RECORDING_STATUS_ERROR
                });
            }.bind(this)
        });
    },
    handleDelete: function (event) {
        event.preventDefault();
        this.props.onRecordingDelete(this.props.mbid);
    },
    render: function () {
        var details = "";
        var rowClassName = "";
        switch (this.state.status) {
            case RECORDING_STATUS_LOADED:
                details = this.state.details.title + " - " + this.state.details.artist;
                rowClassName = "";
                break;
            case RECORDING_STATUS_ERROR:
                details = this.state.error;
                rowClassName = "warning";
                break;
            case RECORDING_STATUS_LOADING:
            default:
                details = <em className="text-muted">loading information</em>;
                rowClassName = "active";
                break;
        }
        return (
            <tr className={rowClassName}>
                <td className="mbid-col">{this.props.mbid}</td>
                <td className="details-col">{details}</td>
                <td className="remove-col">
                    <button type="button" className="close" title="Remove recording"
                            onClick={this.handleDelete}>&times;</button>
                </td>
            </tr>
        );
    }
});


React.render(<Dataset />, container);
