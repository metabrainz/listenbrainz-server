from __future__ import absolute_import
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from flask_wtf import Form
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired
from werkzeug.exceptions import NotFound, Unauthorized, BadRequest
from webserver.external import musicbrainz
from webserver import flash
from collections import defaultdict
import db.dataset
import db.dataset_eval
import db.user
import jsonschema
import csv
import six

datasets_bp = Blueprint("datasets", __name__)


@datasets_bp.route("/<uuid:id>")
def view(id):
    ds = get_dataset(id)
    return render_template(
        "datasets/view.html",
        dataset=ds,
        author=db.user.get(ds["author"]),
    )


@datasets_bp.route("/<uuid:dataset_id>/evaluation")
def eval_info(dataset_id):
    ds = get_dataset(dataset_id)
    return render_template(
        "datasets/eval-info.html",
        dataset=ds,
        author=db.user.get(ds["author"]),
    )


@datasets_bp.route("/<uuid:dataset_id>/evaluation/json")
def eval_jobs(dataset_id):
    # Getting dataset to check if it exists and current user is allowed to view it.
    ds = get_dataset(dataset_id)
    jobs = db.dataset_eval.get_jobs_for_dataset(ds["id"])
    # TODO(roman): Remove unused data ("confusion_matrix", "dataset_id").
    for job in jobs:
        if "result" in job and job["result"]:
            job["result"]["table"] = prepare_table_from_cm(job["result"]["confusion_matrix"])
    return jsonify(jobs=jobs)


@datasets_bp.route("/<uuid:dataset_id>/evaluate")
def evaluate(dataset_id):
    ds = get_dataset(dataset_id)
    if not ds["public"]:
        flash.warn("Can't add private datasets into evaluation queue.")
    else:
        try:
            db.dataset_eval.evaluate_dataset(ds["id"])
            flash.info("Dataset %s has been added into evaluation queue." % ds["id"])
        except db.dataset_eval.IncompleteDatasetException:
            # TODO(roman): Show more informative error message.
            flash.error("Can't add dataset into evaluation queue because it's incomplete.")
        except db.dataset_eval.JobExistsException:
            flash.warn("Evaluation job for this dataset has been already created.")
    return redirect(url_for(".eval_info", dataset_id=dataset_id))


@datasets_bp.route("/<uuid:id>/json")
def view_json(id):
    return jsonify(get_dataset(id))


@datasets_bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    if request.method == "POST":
        dataset_dict = request.get_json()
        if not dataset_dict:
            return jsonify(
                success=False,
                error="Data must be submitted in JSON format.",
            ), 400

        try:
            dataset_id = db.dataset.create_from_dict(dataset_dict, current_user.id)
        except jsonschema.ValidationError as e:
            return jsonify(
                success=False,
                error=str(e),
            ), 400

        return jsonify(
            success=True,
            dataset_id=dataset_id,
        )

    else:  # GET
        return render_template("datasets/edit.html", mode="create")


@datasets_bp.route("/import", methods=("GET", "POST"))
@login_required
def import_csv():
    form = CSVImportForm()
    if form.validate_on_submit():
        dataset_dict = {
            "name": form.name.data,
            "description": form.description.data,
            "classes": _parse_dataset_csv(request.files[form.file.name]),
            "public": False,
        }
        try:
            dataset_id = db.dataset.create_from_dict(dataset_dict, current_user.id)
        except jsonschema.ValidationError as e:
            raise BadRequest(str(e))
        flash.info("Dataset has been imported successfully.")
        return redirect(url_for(".edit", dataset_id=dataset_id))

    else:
        return render_template("datasets/import.html", form=form)


def _parse_dataset_csv(file):
    classes_dict = defaultdict(list)
    for class_row in csv.reader(file):
        if len(class_row) != 2:
            raise BadRequest("Bad dataset! Each row must contain one <MBID, class name> pair.")
        classes_dict[class_row[1]].append(class_row[0])
    classes = []
    for name, recordings in six.iteritems(classes_dict):
        classes.append({
            "name": name,
            "recordings": recordings,
        })
    return classes


@datasets_bp.route("/<uuid:dataset_id>/edit", methods=("GET", "POST"))
@login_required
def edit(dataset_id):
    ds = get_dataset(dataset_id)
    if ds["author"] != current_user.id:
        raise Unauthorized("You can't edit this dataset.")

    if request.method == "POST":
        dataset_dict = request.get_json()
        if not dataset_dict:
            return jsonify(
                success=False,
                error="Data must be submitted in JSON format.",
            ), 400

        try:
            db.dataset.update(str(dataset_id), dataset_dict, current_user.id)
        except jsonschema.ValidationError as e:
            return jsonify(
                success=False,
                error=str(e),
            ), 400

        return jsonify(
            success=True,
            dataset_id=dataset_id,
        )

    else:  # GET
        return render_template(
            "datasets/edit.html",
            mode="edit",
            dataset_id=str(dataset_id),
            dataset_name=ds["name"],
        )


@datasets_bp.route("/<uuid:dataset_id>/delete", methods=("GET", "POST"))
@login_required
def delete(dataset_id):
    ds = get_dataset(dataset_id)
    if ds["author"] != current_user.id:
        raise Unauthorized("You can't delete this dataset.")
    if request.method == "POST":
        db.dataset.delete(ds["id"])
        flash.success("Dataset has been deleted.")
        return redirect(url_for("user.profile", musicbrainz_id=current_user.musicbrainz_id))
    else:  # GET
        return render_template("datasets/delete.html", dataset=ds)


@datasets_bp.route("/recording/<uuid:mbid>")
@login_required
def recording_info(mbid):
    """Endpoint for getting information about recordings (title and artist)."""
    try:
        recording = musicbrainz.get_recording_by_id(mbid)
        return jsonify(recording={
            "title": recording["title"],
            "artist": recording["artist-credit-phrase"],
        })
    except musicbrainz.DataUnavailable as e:
        return jsonify(error=str(e)), 404


class CSVImportForm(Form):
    name = StringField("Name", validators=[DataRequired("Dataset name is required!")])
    description = TextAreaField("Description")
    file = FileField("CSV file", validators=[
        FileRequired(),
        FileAllowed(["csv"], "Dataset needs to be in CSV format!"),
    ])


def get_dataset(dataset_id):
    """Wrapper for `dataset.get` function in `db` package.

    Checks the following conditions and raises NotFound exception if they
    aren't met:
    * Specified dataset exists.
    * Current user is allowed to access this dataset.
    """
    ds = db.dataset.get(dataset_id)
    if ds:
        if ds["public"] or (current_user.is_authenticated()
                            and ds["author"] == current_user.id):
            return ds
    raise NotFound("Can't find this dataset.")


def prepare_table_from_cm(confusion_matrix):
    """Prepares data for table to visualize confusion matrix from Gaia.

    This works with modified version of confusion matrix that we store in our
    database (we store number of recordings in each predicted class instead of
    actual UUIDs of recordings). See gaia_wrapper.py in dataset_eval package
    for implementation details.
    """
    all_classes = set()
    dataset_size = 0  # Number of recordings in the dataset
    for actual_cls in confusion_matrix:
        all_classes.add(actual_cls)
        for predicted_cls in confusion_matrix[actual_cls]:
            # Need to add to class list from there as well because some classes
            # might be missing from the outer dictionary.
            all_classes.add(predicted_cls)
            dataset_size += confusion_matrix[actual_cls][predicted_cls]

    # Sorting to be able to match columns in the table.
    all_classes = sorted(all_classes)

    table_data = {
        "classes": all_classes,
        "rows": [],
    }

    for actual in all_classes:
        # Counting how many tracks were associated with that class during classification
        predicted_class_size = 0
        for predicted in confusion_matrix[actual].values():
            predicted_class_size += predicted

        row = {
            "total": predicted_class_size,
            "proportion": predicted_class_size * 100.0 / dataset_size,
            "predicted": [],
        }

        for predicted in all_classes:
            current_cls = {
                "count": 0,
                "percentage": 0,
            }
            if actual in confusion_matrix:
                if predicted in confusion_matrix[actual]:
                    current_cls["count"] = confusion_matrix[actual][predicted]
                    current_cls["percentage"] = current_cls["count"] * 100.0 / predicted_class_size
            row["predicted"].append(current_cls)

        table_data["rows"].append(row)

    return table_data
