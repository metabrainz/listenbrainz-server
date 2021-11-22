from flask_admin import BaseView, AdminIndexView as IndexView
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from flask import redirect, url_for, current_app

from listenbrainz.webserver import flash


class AuthMixin:
    """All admin views that shouldn't be available to the public must inherit from this."""

    def is_accessible(self):
        if current_user.is_authenticated:
            if current_user.musicbrainz_id in current_app.config['ADMINS']:
                return True
        return False

    def _handle_view(self, name, **kwargs):
        if not self.is_accessible():
            flash.error('You are not authorized to view the admin page.')
            return redirect(url_for('login.index'))


class AdminBaseView(AuthMixin, BaseView): pass


class AdminModelView(AuthMixin, ModelView):
    # Disable creating entries from admin interface
    can_create = False


class AdminIndexView(AuthMixin, IndexView): pass
