import os
import logging

import gazu
from Qt import QtWidgets, QtGui, QtCore

log = logging.getLogger(__name__)


class Login(QtWidgets.QDialog):
    """Log-in dialog to CG-Wire"""

    on_login_signal = QtCore.Signal(bool)

    def __init__(self, parent=None, initialize_host=True):
        super(Login, self).__init__(parent)

        self.setWindowTitle("Log-in to CGWire")

        form = QtWidgets.QFormLayout()
        form.setContentsMargins(10, 15, 10, 5)
        form.setObjectName("form")

        # Host
        host_label = QtWidgets.QLabel("CG-Wire URL:")
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
        error = QtWidgets.QLabel()
        error.hide()
        error.setStyleSheet("""QLabel { 
            background-color: #CC4444; 
            color: #F5F5F5; 
            padding: 5px;
        }""")

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
                log.debug("Setting CG-Wire host "
                          "from gazu.client: %s" % gazu_host)
                host = gazu_host
        else:
            log.debug("Setting CG-Wire host from environment "
                      "variable CGWIRE_HOST: %s" % host)

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
            result = gazu.log_in(user, password)
        except Exception as exc:

            message = str(exc)
            if message.startswith("('auth/login',"):
                # Failed to login
                message = "Login verification failed.\n" \
                          "Please ensure your username and " \
                          "password are correct."
            else:
                # Something else happened.
                # For readability produce new line
                # around every dot with following space
                message = message.replace(". ", ".\n")

            self.error.setText(message)
            self.error.show()
            self.on_login_signal.emit(False)
            return

        if result:
            name = "{user[first_name]} {user[last_name]}".format(**result)
            log.info("Logged in as %s.." % name)
            self.on_login_signal.emit(True)
        self.accept()
