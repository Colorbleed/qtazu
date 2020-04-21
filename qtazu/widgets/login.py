import os
import logging
import re

import gazu
from Qt import QtWidgets, QtGui, QtCore

log = logging.getLogger(__name__)

PLACEHOLDER = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "res", "image", "logo_kitsu.png"
)


class AnimatedLabel(QtWidgets.QLabel):
    """
    QLabel with animated background color.
    """

    def __init__(self):
        super(AnimatedLabel, self).__init__()
        self.setStyleSheet(
            """
            background-color: #CC4444;
            color: #F5F5F5;
            padding: 5px;
            """
        )
        self.setWordWrap(True)
        self.create_animation()

    def create_animation(self):
        """
        Create the animation of the color background.
        """
        color_begin = QtGui.QColor("#943434")
        color_end = QtGui.QColor("#CC4444")
        byar = QtCore.QByteArray()
        byar.append("zcolor")
        self.color_anim = QtCore.QPropertyAnimation(self, byar)
        self.color_anim.setStartValue(color_begin)
        self.color_anim.setEndValue(color_end)
        self.color_anim.setDuration(400)

    def start_animation(self):
        """
        Start the animation of the color background.
        """
        self.color_anim.stop()
        self.color_anim.start()

    def parse_style_sheet(self):
        """
        Return a list with style sheet instructions.
        """
        ss = self.styleSheet()
        sts = [s.strip() for s in ss.split(';') if len(s.strip())]
        return sts

    def get_back_color(self):
        """
        Get the background color.
        """
        return self.palette().color(QtGui.QPalette.Window)

    def set_back_color(self, color):
        """
        Set the given color as background color by parsing the style sheet.
        """
        sss = self.parse_style_sheet()
        bg_new = 'background-color: %s' % color.name()

        for k, sty in enumerate(sss):
            if re.search('\Abackground-color:', sty):
                sss[k] = bg_new
                break
        else:
            sss.append(bg_new)

        self.setStyleSheet('; '.join(sss))

    # Property to animate : the label background color
    zcolor = QtCore.Property(QtGui.QColor, get_back_color, set_back_color)


class Login(QtWidgets.QDialog):
    """Log-in dialog to CG-Wire"""

    logged_in = QtCore.Signal(bool)

    def __init__(self, parent=None, initialize_host=True):
        super(Login, self).__init__(parent)

        self.setWindowTitle("Connect your app to Kitsu")

        # Kitsu logo
        logo_label = QtWidgets.QLabel()
        pixmap = QtGui.QPixmap()
        pixmap.load(PLACEHOLDER)
        logo_label.setPixmap(pixmap)
        logo_label.setAlignment(QtCore.Qt.AlignCenter)

        form = QtWidgets.QFormLayout()
        form.setContentsMargins(10, 15, 10, 5)
        form.setObjectName("form")

        # Host
        host_label = QtWidgets.QLabel("Kitsu URL:")
        host_input = QtWidgets.QLineEdit()
        host_input.setPlaceholderText("https://xxx.cg-wire.com/api")

        # User
        user_label = QtWidgets.QLabel("Username:")
        user_input = QtWidgets.QLineEdit()
        user_input.setPlaceholderText("user@host.com")

        # Password
        password_label = QtWidgets.QLabel("Password:")
        password_input = QtWidgets.QLineEdit()
        password_input.setEchoMode(QtWidgets.QLineEdit.Password)

        # Error
        error = AnimatedLabel()
        error.hide()

        # Buttons
        login = QtWidgets.QPushButton("Login")
        login.setAutoDefault(True)
        login.setDefault(True)
        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(login)

        form.addRow(host_label, host_input)
        form.addRow(user_label, user_input)
        form.addRow(password_label, password_input)

        self.inputs = dict()
        self.inputs["host"] = host_input
        self.inputs["user"] = user_input
        self.inputs["password"] = password_input
        self.error = error

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(logo_label)
        layout.addLayout(form)
        layout.addWidget(error)
        layout.addLayout(buttons)

        self.resize(325, 160)

        # Connections
        login.clicked.connect(self.on_login)

        if initialize_host:
            # Automatically enter host if available.
            self.initialize_host()

    def initialize_host(self):
        """Initialize host value based on environment"""

        host_input = self.inputs["host"]

        host = os.environ.get("CGWIRE_HOST", None)
        if host is None:
            gazu_host = gazu.client.get_host()
            if gazu_host != "http://gazu.change.serverhost/api":
                # Assume the host in gazu.client is already set correctly
                # and copy it into these settings.
                log.debug(
                    "Setting CG-Wire host " "from gazu.client: %s" % gazu_host
                )
                host = gazu_host
        else:
            log.debug(
                "Setting CG-Wire host from environment "
                "variable CGWIRE_HOST: %s" % host
            )

        if host:
            # Force the host by environment variable
            host_input.setText(host)
            host_input.setEnabled(False)
        else:
            host_input.setEnabled(True)

    def on_login(self):
        """Perform login with current settings in the dialog."""

        host = self.inputs["host"].text()
        user = self.inputs["user"].text()
        password = self.inputs["password"].text()

        try:
            gazu.set_host(host)
            if not gazu.client.host_is_up():
                raise ConnectionError(
                    "Could not connect to the server. Is the host URL correct ?"
                )
            result = gazu.log_in(user, password)
        except Exception as exc:
            message = str(exc)
            if message.startswith("auth/login"):
                message = (
                    "Could not connect to the server. Is the host URL correct ?"
                )
            if message.startswith("('auth/login',"):
                # Failed to login
                message = (
                    "Login verification failed.\n"
                    "Please ensure your username and "
                    "password are correct."
                )
            else:
                # Something else happened.
                # For readability produce new line
                # around every dot with following space
                message = message.replace(". ", ".\n")

            self.error.setText(message)
            self.error.show()
            self.error.start_animation()
            self.logged_in.emit(False)
            return

        if result:
            name = "{user[first_name]} {user[last_name]}".format(**result)
            log.info("Logged in as %s.." % name)
            self.logged_in.emit(True)
        self.accept()
