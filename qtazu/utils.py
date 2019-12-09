import sys
import logging
import requests.exceptions

import gazu
from Qt import QtCore

log = logging.getLogger(__name__)


def get_cgwire_data(data):
    """Return data from CG-Wire using `type` and `id`.

    Args:
        data (dict): Dictionary containing "type" and "id" of the query.

    Returns:
         dict: The result from Gazu.

    """

    assert "type" in data
    assert "id" in data

    fn_name = data["type"].lower()

    # Get the module (e.g. gazu.project, gazu.asset, gazu.shot)
    module = getattr(gazu, fn_name)

    # Request the result by id
    fn = getattr(module, "get_{0}".format(fn_name))
    return fn(data["id"])


def get_web_url(entity=None):
    """Get the web url for the given entity

    Note: This might not work with all entity types!

    """
    # todo: continue implementation (only tested with "tasks" for now)

    conversion = {
        "TaskType": "task-types",
        "Project": "productions",
        "Person": "people",
        "Asset": "assets",
        "Shot": "shots",
        "Task": "tasks"
    }

    def _format_url(entity):
        """Format the URL element for an entity"""
        entity_type = entity["type"]
        return "/{type}/{id}".format(type=conversion[entity_type],
                                     id=entity["id"])

    # Get base URL from current host
    host_api = gazu.client.get_host()
    url = host_api[:-4]  # remove '/api'

    # When no entity is given just go to the base CG-Wire page.
    if entity is None:
        return url

    # Ensure we get the "full" entity with parent data
    entity = get_cgwire_data(entity)

    if entity["type"] == "Task":
        # /productions/{project-id}/{for_entity}/tasks/{task_id}
        # parent: 'assets' or 'shots'
        parent = conversion[entity["task_type"]["for_entity"]]
        return (
            url + _format_url(entity["project"]) +
            "/" + parent + _format_url(entity)
        )
    elif entity["type"] == "Asset" or entity["type"] == "Shot":
        # For assets and shots it must be prefixed with project
        return url + _format_url(entity["project"]) + _format_url(entity)

    return url + _format_url(entity)


def is_valid_api_url(url):
    """Return whether the API url is valid for zou/gazu

    This checks the JSON response from the `host/api` url
    to see whether it contains the api == Zou value.

    Returns:
        bool: Whether the url is the /api url for CG-Wire's zou.

    """
    # Just use the gazu client's request session
    session = gazu.client.requests_session

    result = session.get(url)
    if result.status_code != 200:
        # The status is not as expected from a valid CG-Wire zou
        # api url. So we consider this to be an invalid response.
        return False

    try:
        data = result.json()
    except ValueError as exc:
        # If not JSON data can be decoded we assume it's an invalid
        # api url.
        return False

    if "api" in data and "version" in data and data["api"] == "Zou":
        return True

    return False


def is_logged_in():
    """Return whether you are currently logged in with Gazu"""

    try:
        user = gazu.client.get_current_user()
        if user:
            return True
    except (gazu.exception.NotAuthenticatedException,
            requests.exceptions.ConnectionError):
        # If we are not authenticated assume we are not
        # logged in and allow it to pass.
        pass

    return False


def log_out():
    """Log out from Gazu by clearing its access tokens."""
    tokens = {
        "access_token": "",
        "refresh_token": ""
    }
    gazu.client.tokens = tokens


class Worker(QtCore.QThread):
    """Perform work in a background thread."""

    def __init__(self, function, args=None, kwargs=None, parent=None):
        """Execute *function* in separate thread.

        It stores the threaded function call's result in `self.result`.
        When an exception occurs the error is stored in `self.error`

        Args:
            function (function): The function that will be threaded.
            args (tuple or list): positional arguments
            kwargs (dict): keyword arguments to pass to the function
                           on execution.
            parent (QtCore.QObject): The parent Qt object.

        Example usage:

            try:
                worker = Worker(fn, args=[42])
                worker.start()

                while worker.isRunning():
                    app = QtGui.QApplication.instance()
                    app.processEvents()

                if worker.error:
                    raise worker.error[1], None, worker.error[2]

            except Exception as error:
                traceback.print_exc()

        """
        super(Worker, self).__init__(parent=parent)
        self.function = function
        self.args = args or []
        self.kwargs = kwargs or {}
        self.result = None
        self.error = None

    def run(self):
        """Execute function and store result."""
        try:
            self.result = self.function(*self.args, **self.kwargs)
        except Exception:
            self.error = sys.exc_info()
