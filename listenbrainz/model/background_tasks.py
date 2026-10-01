import json

from markupsafe import Markup
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB

from listenbrainz.model import db
from listenbrainz.model.utils import generate_username_link
from listenbrainz.webserver.admin import AdminModelView


class BackgroundTask(db.Model):
    __tablename__ = 'background_tasks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    task = db.Column(db.String, nullable=False)
    created = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    # "metadata" is reserved by SQLAlchemy's declarative models.
    task_metadata = db.Column('metadata', JSONB)
    claimed_at = db.Column(db.DateTime(timezone=True))
    user = db.relationship('User')


def format_metadata(view, context, model, name):
    if model.task_metadata is None:
        return ''
    return Markup('<details><summary>Click to expand</summary><pre>{}</pre></details>').format(
        json.dumps(model.task_metadata, indent=2, sort_keys=True)
    )


class BackgroundTasksAdminView(AdminModelView):
    can_create = False
    can_edit = False
    can_delete = False

    column_list = [
        'id', 'user_id', 'user_name', 'task', 'created', 'claimed_at',
        'progress_status', 'progress', 'task_metadata',
    ]
    column_labels = {
        'task_metadata': 'Metadata',
        'progress_status': 'Import/export status',
    }
    column_descriptions = {
        'claimed_at': 'When a worker claimed this task; this does not indicate whether it is still running.',
        'progress': 'Latest recorded import/export progress. Refresh the page to update.',
    }
    column_searchable_list = ['id', 'user_id', 'user.musicbrainz_id', 'task']
    column_filters = ['user_id', 'task', 'created', 'claimed_at']
    column_default_sort = [('created', False), ('id', False)]
    column_select_related_list = [BackgroundTask.user]
    column_formatters = {
        'user_name': lambda view, context, model, name: generate_username_link(model.user.musicbrainz_id),
        'task_metadata': format_metadata,
    }

    def get_list(self, *args, **kwargs):
        count, tasks = super().get_list(*args, **kwargs)
        for task in tasks:
            task.progress_status = 'Not available'
            task.progress = 'Not available'

        # Fetch related progress only for the current page, without a query per task.
        for task_type, metadata_key, query in [
            ('import_listens', 'import_id', """
                SELECT id, user_id, metadata->>'status' AS status, metadata->>'progress' AS progress
                  FROM user_data_import
                 WHERE id IN :ids
            """),
            ('export_all_user_data', 'export_id', """
                SELECT id, user_id, status, progress
                  FROM user_data_export
                 WHERE id IN :ids
            """),
        ]:
            related_tasks = [task for task in tasks if task.task == task_type]
            ids = {
                task.id: task.task_metadata.get(metadata_key)
                if isinstance(task.task_metadata, dict) else None
                for task in related_tasks
            }
            # Missing or malformed metadata must not prevent the queue from rendering.
            valid_ids = {value for value in ids.values() if type(value) is int and 0 < value <= 2147483647}
            progress = {}
            if valid_ids:
                rows = self.session.execute(
                    text(query).bindparams(bindparam('ids', expanding=True)),
                    {'ids': sorted(valid_ids)},
                ).mappings()
                progress = {(row['id'], row['user_id']): row for row in rows}
            for task in related_tasks:
                record_id = ids[task.id]
                record = progress.get((record_id, task.user_id)) if type(record_id) is int else None
                if record is None:
                    task.progress = 'Related record unavailable'
                else:
                    task.progress_status = record['status'] or 'Not available'
                    task.progress = record['progress'] or 'Not available'

        return count, tasks
