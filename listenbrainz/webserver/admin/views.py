from flask import redirect, request
from flask_admin import expose

from listenbrainz.listenstore.redis_listenstore import RedisListenStore
from listenbrainz.webserver import flash
from listenbrainz.webserver import redis_connection
from listenbrainz.webserver.admin import AdminBaseView, AdminIndexView


class HomeView(AdminIndexView):

    @expose('/')
    def index(self):
        return self.render('admin/home.html')


class AdminFlashMessagesView(AdminBaseView):

    @expose('/')
    def index(self):
        return self.render(
            'admin/flash_messages.html',
            messages=redis_connection._redis.get_admin_flash_messages(),
            levels=RedisListenStore.ADMIN_FLASH_MESSAGE_LEVELS,
        )

    @expose('/add', methods=['POST'])
    def add(self):
        level = request.form.get('level', '').strip()
        message = request.form.get('message', '').strip()

        if level not in RedisListenStore.ADMIN_FLASH_MESSAGE_LEVELS:
            flash.error('Invalid flash message level.')
        elif not message:
            flash.error('Flash message cannot be empty.')
        else:
            redis_connection._redis.add_admin_flash_message(level, message)
            flash.success('Flash message added.')

        return redirect(self.get_url('.index'))

    @expose('/edit/<message_id>', methods=['POST'])
    def edit(self, message_id):
        level = request.form.get('level', '').strip()
        message = request.form.get('message', '').strip()

        if level not in RedisListenStore.ADMIN_FLASH_MESSAGE_LEVELS:
            flash.error('Invalid flash message level.')
        elif not message:
            flash.error('Flash message cannot be empty.')
        elif redis_connection._redis.update_admin_flash_message(message_id, level, message):
            flash.success('Flash message updated.')
        else:
            flash.error('Flash message not found.')

        return redirect(self.get_url('.index'))

    @expose('/delete/<message_id>', methods=['POST'])
    def delete(self, message_id):
        if redis_connection._redis.delete_admin_flash_message(message_id):
            flash.success('Flash message deleted.')
        else:
            flash.error('Flash message not found.')

        return redirect(self.get_url('.index'))
