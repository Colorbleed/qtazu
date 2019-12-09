import os
import sys
import gazu
from Qt import QtWidgets, QtCore, QtGui

from ..utils import Worker


# Cache of thumbnail images.
IMAGE_CACHE = dict()
PLACEHOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           "res", "icon", "no_thumbnail.png")


class ThumbnailBase(QtWidgets.QLabel):
    """Widget to load thumbnails from CG-Wire server through gazu.

    This asynchronously loads Thumbnails in Worker Threads.

    """

    def __init__(self, parent=None):
        super(ThumbnailBase, self).__init__(parent)

        self.thumbnailCache = {}
        self.setFrameStyle(QtWidgets.QFrame.StyledPanel)
        self.setAlignment(QtCore.Qt.AlignCenter)

        self.placeholderThumbnail = PLACEHOLDER

        self._worker = None
        self.__loadingReference = None

    def load(self, reference):
        """Load thumbnail from *reference* and display it."""

        if reference in IMAGE_CACHE:
            self._updatePixmapData(IMAGE_CACHE[reference])
            return

        if self._worker and self._worker.isRunning():
            while self._worker:
                app = QtWidgets.QApplication.instance()
                app.processEvents()

        self._worker = Worker(self._download, [reference], parent=self)
        self.__loadingReference = reference
        self._worker.start()
        self._worker.finished.connect(self._workerFinished)

    def _workerFinished(self):
        """Handler worker finished event."""

        if self._worker:

            pixmap = self._worker.result
            if not pixmap:
                # If not image downloaded read the thumbnail
                # placeholder instead
                qfile = QtCore.QFile(self.placeholderThumbnail)
                qfile.open(qfile.ReadOnly)
                pixmap = qfile.readAll()

            IMAGE_CACHE[self.__loadingReference] = pixmap
            self._updatePixmapData(pixmap)

        self._worker = None
        self.__loadingReference = None

    def _updatePixmapData(self, data):
        """Update thumbnail with *data*."""
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(data)
        self._scaleAndSetPixmap(pixmap)

    def _scaleAndSetPixmap(self, pixmap):
        """Scale and set *pixmap*."""
        scaledPixmap = pixmap.scaledToWidth(
            self.width(),
            mode=QtCore.Qt.SmoothTransformation
        )
        self.setPixmap(scaledPixmap)

    def _download(self, url):
        """Return thumbnail file from *url*.

        Args:
            url (str): The relative url in the form of
                'pictures/thumbnails/{type}/{id}.png'

        """
        full_url = gazu.client.get_full_url(url)
        requests_session = gazu.client.requests_session

        with requests_session.get(
            full_url,
            headers=gazu.client.make_auth_header(),
            stream=True
        ) as response:
            bytes = QtCore.QByteArray()
            for chunk in response.iter_content(8192):
                bytes.append(chunk)

            return bytes
