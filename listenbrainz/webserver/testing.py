import unittest
from urllib import parse

from flask import template_rendered, message_flashed

from listenbrainz.webserver import create_api_compat_app, create_web_app


class ServerTestCase(unittest.TestCase):
    """ TestCase for Flask App tests, most of the code here has been borrowed from flask_testing.TestCase
    (https://github.com/jarus/flask-testing/blob/5107691011fa891835c01547e73e991c484fa07f/flask_testing/utils.py#L118).
    A key difference is that flask_testing's TestCase creates the flask app for each test method whereas
    our ServerTestCase creates it once per class. flask_testing's test case allows also for custom Response mixins
    and other stuff to be compatible across flask versions. Since, we don't need that the implementation can be
    simplified.

    Notably, the implementation of the setUpClass, setUp, tearDown, tearDownClass, assertMessageFlashed,
    assertTemplateUsed has been adapted to use class level variables. The implementation of assertRedirects has been
    modified to fix concerning absolute and relative urls in Location header.
    """

    @classmethod
    def create_app(cls):
        app = create_web_app(debug=False)
        app.config['TESTING'] = True
        return app

    def temporary_login(self, user_login_id):
        with self.client.session_transaction() as session:
            session['_user_id'] = user_login_id
            session['_fresh'] = True

    @classmethod
    def setUpClass(cls):
        cls.app = cls.create_app()
        cls.client = cls.app.test_client()

        server_name = cls.app.config.get("SERVER_NAME")
        if server_name is None:
            server_name = "localhost"
        cls.url_adapter = cls.app.url_map.bind(server_name)

        template_rendered.connect(cls._set_template)
        message_flashed.connect(cls._add_flash_message)

        cls.template = None
        cls.flashed_messages = []

    def setUp(self) -> None:
        ServerTestCase.template = None
        ServerTestCase.flashed_messages = []

    @classmethod
    def _add_flash_message(cls, app, message, category):
        cls.flashed_messages.append((message, category))

    @classmethod
    def _set_template(cls, app, template, context):
        cls.template = (template, context)

    def tearDown(self):
        del ServerTestCase.template
        del ServerTestCase.flashed_messages

    @classmethod
    def tearDownClass(cls):
        template_rendered.disconnect(cls._set_template)
        message_flashed.disconnect(cls._add_flash_message)
        del cls.client
        del cls.app

    def custom_url_for(self, endpoint, **values):
        """ A custom version of Flask's url_for() that does not require an active app context.

            Note that this function is not on feature parity with Flask's url_for() and only supports the
            basic use cases we have.
        """
        force_external = values.pop('force_external', False)
        return self.url_adapter.build(endpoint, values, force_external=force_external)

    def assertMessageFlashed(self, message, category='message'):
        """
        Checks if a given message was flashed.
        Only works if your version of Flask has message_flashed
        signal support (0.10+) and blinker is installed.
        :param message: expected message
        :param category: expected message category
        """
        for _message, _category in ServerTestCase.flashed_messages:
            if _message == message and _category == category:
                return True

        raise AssertionError("Message '%s' in category '%s' wasn't flashed" % (message, category))

    def assertTemplateUsed(self, name):
        """
        Checks if a given template is used in the request.
        Only works if your version of Flask has signals
        support (0.6+) and blinker is installed.
        If the template engine used is not Jinja2, provide
        ``tmpl_name_attribute`` with a value of its `Template`
        class attribute name which contains the provided ``name`` value.
        :versionadded: 0.2
        :param name: template name
        """
        if ServerTestCase.template is None:
            self.fail("No template used")
        used_template = ServerTestCase.template[0].name
        self.assertEqual(used_template, name, f"Template {name} not used. Template used: {used_template}")

    def get_context_variable(self, name):
        if ServerTestCase.template is None:
            self.fail("No template used")
        context = ServerTestCase.template[1]
        if name in context:
            return context[name]
        raise ValueError()

    def assertContext(self, name, value, message=None):
        try:
            self.assertEqual(self.get_context_variable(name), value, message)
        except ValueError:
            self.fail(message or "Context variable does not exist: %s" % name)

    assert_context = assertContext

    def assertRedirects(self, response, location, message=None, permanent=False):
        if permanent:
            valid_status_codes = (301, 308)
        else:
            valid_status_codes = (301, 302, 303, 305, 307, 308)

        valid_status_code_str = ', '.join(str(code) for code in valid_status_codes)
        not_redirect = f"HTTP Status {valid_status_code_str} expected but got {response.status_code}"

        self.assertIn(response.status_code, valid_status_codes, message or not_redirect)

        response_location = parse.unquote(response.location)
        location_mismatch = f"Expected redirect location {location} but got {response_location}"
        self.assertTrue(response_location.endswith(location), message or location_mismatch)

    def assertStatus(self, response, status_code, message=None):
        message = message or 'HTTP Status %s expected but got %s' \
                             % (status_code, response.status_code)
        self.assertEqual(response.status_code, status_code, message)

    def assert200(self, response, message=None):
        self.assertStatus(response, 200, message)

    def assert400(self, response, message=None):
        self.assertStatus(response, 400, message)

    def assert401(self, response, message=None):
        self.assertStatus(response, 401, message)

    def assert403(self, response, message=None):
        self.assertStatus(response, 403, message)

    def assert404(self, response, message=None):
        self.assertStatus(response, 404, message)

    def assert500(self, response, message=None):
        self.assertStatus(response, 500, message)


class ServerAppPerTestTestCase(ServerTestCase):
    """ Same functionality as ServerTestCase but the flask app is created for each test method.
        Useful when you want to call/test setup methods for app or blueprints in tests, for instance
        to register new routes.
    """

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self) -> None:
        self.app = self.create_app()
        self.client = self.app.test_client()

        template_rendered.connect(self._set_template)
        message_flashed.connect(self._add_flash_message)
        self.template = None
        self.flashed_messages = []

        self._ctx = self.app.test_request_context()
        self._ctx.push()

    def tearDown(self) -> None:
        self._ctx.pop()
        del self._ctx

        del self.template
        del self.flashed_messages
        template_rendered.disconnect(self._set_template)
        message_flashed.disconnect(self._add_flash_message)

    def _add_flash_message(self, app, message, category):
        self.flashed_messages.append((message, category))

    def _set_template(self, app, template, context):
        self.template = (template, context)

    def assertMessageFlashed(self, message, category='message'):
        """
        Checks if a given message was flashed.
        Only works if your version of Flask has message_flashed
        signal support (0.10+) and blinker is installed.
        :param message: expected message
        :param category: expected message category
        """
        for _message, _category in self.flashed_messages:
            if _message == message and _category == category:
                return True

        raise AssertionError("Message '%s' in category '%s' wasn't flashed" % (message, category))

    def assertTemplateUsed(self, name):
        """
        Checks if a given template is used in the request.
        Only works if your version of Flask has signals
        support (0.6+) and blinker is installed.
        If the template engine used is not Jinja2, provide
        ``tmpl_name_attribute`` with a value of its `Template`
        class attribute name which contains the provided ``name`` value.
        :versionadded: 0.2
        :param name: template name
        """
        if self.template is None:
            self.fail("No template used")
        used_template = self.template[0].name
        self.assertEqual(used_template, name, f"Template {name} not used. Template used: {used_template}")

    def get_context_variable(self, name):
        if self.template is None:
            self.fail("No template used")
        context = self.template[1]
        if name in context:
            return context[name]
        raise ValueError()


class APICompatServerTestCase(ServerTestCase):

    @classmethod
    def create_app(cls):
        app = create_api_compat_app()
        app.config['TESTING'] = True
        return app
