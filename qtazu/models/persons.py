import logging

from Qt import QtWidgets, QtCore, QtGui
import gazu

from ..utils import Worker

log = logging.getLogger(__name__)


class PersonModel(QtCore.QAbstractListModel):
    """List model displaying CG-Wire Persons with Thumbnail

    The thumbnails are loaded from the server in an async fashion to avoid
    lockups of the user interface during this load.

    """
    def __init__(self):
        super(PersonModel, self).__init__()

        pixmap = QtGui.QPixmap(QtCore.QSize(30, 30))
        pixmap.fill(QtGui.QColor(0, 0, 0, 0))
        self._empty_icon = QtGui.QIcon(pixmap)
        self._list = []
        self._persons = []
        self._worker = None
        self.refresh()

    def refresh(self):

        persons = gazu.person.all_persons()

        # Initialize icons to an empty icon but allow the threaded worker
        # to update it later so these thumbnails are collected
        # without hanging the local UI.
        for entry in persons:
            entry["_icon"] = self._empty_icon

        # Store by id and keep the list in an order by ids only
        self._list = [person["id"] for person in persons]  # the ordered list
        self._persons = {person["id"]: person for person in persons}

        # Set up Worker to collect the avatars for those that have an avatar
        ids_with_avatar = [person["id"] for person in persons
                           if person["has_avatar"]]
        self.download_icons(ids_with_avatar)

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._list)

    def _format_person_name(self, person):
        return u"{0[first_name]} {0[last_name]}".format(person)

    def data(self, index, role):
        if index.isValid():
            person_id = self._list[index.row()]
            person = self._persons[person_id]

            if role == QtCore.Qt.DisplayRole:
                return self._format_person_name(person)

            if role == QtCore.Qt.DecorationRole:
                return person["_icon"]

            if role == QtCore.Qt.EditRole:
                return self._format_person_name(person)

    def download_icons(self, ids):
        """Load thumbnail from *reference* and display it."""

        if self._worker and self._worker.isRunning():
            while self._worker:
                app = QtWidgets.QApplication.instance()
                app.processEvents()

        # We don't set "self" as the parent for the Worker
        # as somehow that ends up crashing now and then...
        self._worker = Worker(self._download_icons, [ids])
        self._worker.start()
        self._worker.finished.connect(self._workerFinished)

    def _workerFinished(self):
        """Handler worker finished event."""

        top = self.index(0)
        bottom = self.index(self.rowCount())

        self._pixmaps = []
        self._icons = []

        if self._worker:
            result = self._worker.result
            if result:
                for id, bytes in result.items():

                    # Generate pixmap from bytes
                    pixmap = QtGui.QPixmap()
                    pixmap.loadFromData(bytes)
                    self._pixmaps.append(pixmap)

                    if pixmap.isNull():
                        # Downloaded bytes are invalid
                        log.warning("Invalid bytes..")
                        continue

                    mode = QtCore.Qt.SmoothTransformation
                    pixmap = pixmap.scaledToWidth(30, mode=mode)

                    # Generate icon from pixmap
                    icon = QtGui.QIcon(pixmap)
                    self._icons.append(icon)

                    # Store the icon on the person
                    self._persons[id]["_icon"] = icon

                log.debug("Finished setting icons..")

        self.dataChanged.emit(top, bottom, [QtCore.Qt.DecorationRole])

        log.debug("Finished emitting data changed")
        self._worker = None

    def _download_icons(self, ids):
        """Return thumbnail for person file from *url*.

        Args:
            url (str): The relative url in the form of
                'pictures/thumbnails/{type}/{id}.png'

        """

        # Create our session
        import requests
        session = requests.Session()
        header = gazu.client.make_auth_header()

        data = {}
        for person_id in ids:

            url = "pictures/thumbnails/persons/{0}.png".format(person_id)
            full_url = gazu.client.get_full_url(url)

            with session.get(
                full_url,
                headers=header,
                stream=True
            ) as response:

                if response.status_code != 200:
                    # Request failed
                    log.error("Failed request: %s" % full_url)
                    continue

                bytes = QtCore.QByteArray()
                for chunk in response.iter_content(8192):
                    bytes.append(chunk)

                if not bytes.isNull():
                    data[person_id] = bytes

        return data
