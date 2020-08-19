"""
Retrieve data metrics from all network adaptator.

This module is maintained by Mickaël Schoentgen <contact@tiger-222.fr>.

You can always get the latest version of this module at:
    https://github.com/BoboTiG/trafic
If that URL should fail, try contacting the author.
"""
import sys
from contextlib import suppress
from pathlib import Path

from PyQt5.QtCore import QUrl, Qt, QTimer
from PyQt5.QtGui import QDesktopServices, QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QMenu,
    QMessageBox,
    QStyle,
    QSystemTrayIcon,
    QTextEdit,
    QVBoxLayout,
)

from . import __version__
from .constants import APP_NAME, COLOR_DOWN, COLOR_UP, ICON_DOWN, ICON_UP
from .utils import get_stats, sizeof_fmt
from .worker import Worker


# Enable High-DPI
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)


class Application(QApplication):
    def __init__(self, db_file: str):
        QApplication.__init__(self, [])

        # Little trick here!
        #
        # Qt strongly builds on a concept called event loop.
        # Such an event loop enables you to write parallel applications without multithreading.
        # The concept of event loops is especially useful for applications where
        # a long living process needs to handle interactions from a user or client.
        # Therefore, you often will find event loops being used in GUI or web frameworks.
        #
        # However, the pitfall here is that Qt is implemented in C++ and not in Python.
        # When we execute app.exec_() we start the Qt/C++ event loop, which loops
        # forever until it is stopped.
        #
        # The problem here is that we don't have any Python events set up yet.
        # So our event loop never churns the Python interpreter and so our signal
        # delivered to the Python process is never processed. Therefore, our
        # Python process never sees the signal until we hit some button of
        # our Qt application window.
        #
        # To circumvent this problem is very easy. We just need to set up a timer
        # kicking off our event loop every few milliseconds.
        #
        # https://machinekoder.com/how-to-not-shoot-yourself-in-the-foot-using-python-qt/
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: None)
        self.timer.start(100)

        self.db = db_file

        self.tray_icon = SystemTrayIcon(self)
        self.tray_icon.show()

        if hasattr(sys, "frozen") and sys.platform.startswith("win"):
            self._check_for_update()

        self.worker = Worker(self, self.db)

    def output(self, msg: str) -> None:
        """Change the system tray tooltip."""
        self.tray_icon.setToolTip(msg)

    def _check_for_update(self) -> None:
        """Check for a new update."""
        try:
            from . import __version__
            from .updater.windows import Updater

            updater = Updater(self.tray_icon.setToolTip)
            updater.check(__version__)
        except Exception as exc:
            print(f"Erreur de MàJ automatique ({exc})", flush=True)


class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, app: Application) -> None:
        QSystemTrayIcon.__init__(self)

        self.app = app

        icon = Path(getattr(sys, "_MEIPASS", ".")) / "trafic.svg"
        self.icon = QIcon(str(icon))
        self.setIcon(self.icon)

        self.create_menu()
        self._dialog: QDialog = None

    def create_menu(self) -> None:
        """Create the context menu."""
        menu = QMenu()
        style = QApplication.style()
        func = style.standardIcon

        for icon, label, func in (
            (func(QStyle.SP_FileDialogContentsView), "Statistiques", self.open_stats),
            (func(QStyle.SP_FileDialogDetailedView), "Données brutes", self.open_file),
            (func(QStyle.SP_DialogCloseButton), "Quitter", self.exit),
        ):
            action = menu.addAction(icon, label)
            action.triggered.connect(func)

        self.setContextMenu(menu)

    def _display_message(self, icon: QIcon, title: str, message: str) -> None:
        """Display a generic message box warning."""
        msg = QMessageBox()
        msg.setWindowTitle(title)
        msg.setWindowIcon(self.icon)
        msg.setIcon(icon)
        msg.setTextFormat(Qt.RichText)
        msg.setText(message)
        msg.exec_()

    def display_info(self, title: str, message: str) -> None:
        """Display a generic message box information."""
        self._display_message(QMessageBox.Information, title, message)

    def display_warning(self, title: str, message: str) -> None:
        """Display a generic message box warning."""
        self._display_message(QMessageBox.Warning, title, message)

    def exit(self) -> None:
        """Quit the current application."""
        self.hide()
        if hasattr(self.app, "worker"):
            self.app.worker.need_to_run = False
            self.app.worker.thr.join()
        self.app.exit()

    def open_file(self) -> None:
        """Open the metrics database file.  It requires a SQLite database browser."""
        url = QUrl.fromLocalFile(self.app.db)
        if not QDesktopServices.openUrl(url):
            msg = "Veuillez installer <a href='https://sqlitebrowser.org/dl/'>DB Browser for SQLite</a>."
            self.display_warning(APP_NAME, msg)

    def open_stats(self) -> None:
        """Open a message box with simple metrics."""
        if self._dialog:
            with suppress(RuntimeError):
                # Skip RuntimeError: wrapped C/C++ object of type QDialog has been deleted
                self._dialog.destroy()
            self._dialog = None

        metrics = get_stats(self.app.db)
        html = f"""
<h2 style="text-align: center">Statistiques Basiques</h2>
<hr/>

<ul style="list-style-type: none">
    <li>Aujourd'hui :
        <ul style="list-style-type: none">
            <li style="color: {COLOR_DOWN}">{ICON_DOWN} {sizeof_fmt(metrics["1d"]["r"])}</li>
            <li style="color: {COLOR_UP}">{ICON_UP} {sizeof_fmt(metrics["1d"]["s"])}</li>
        </ul>
    </li>
    <li style="margin-top: 10px">Ces 7 derniers jours :
        <ul style="list-style-type: none">
            <li style="color: {COLOR_DOWN}">{ICON_DOWN} {sizeof_fmt(metrics["7d"]["r"])}</li>
            <li style="color: {COLOR_UP}">{ICON_UP} {sizeof_fmt(metrics["7d"]["s"])}</li>
        </ul>
    </li>
    <li style="margin-top: 10px">Ces 30 derniers jours :
        <ul style="list-style-type: none">
            <li style="color: {COLOR_DOWN}">{ICON_DOWN} {sizeof_fmt(metrics["30d"]["r"])}</li>
            <li style="color: {COLOR_UP}">{ICON_UP} {sizeof_fmt(metrics["30d"]["s"])}</li>
        </ul>
    </li>
    <li style="margin-top: 10px"> <b>TOTAL</b> ({metrics["total"]["d"]} jours) :
        <ul style="list-style-type: none">
            <li style="color: {COLOR_DOWN}">{ICON_DOWN} {sizeof_fmt(metrics["total"]["r"])}</li>
            <li style="color: {COLOR_UP}">{ICON_UP} {sizeof_fmt(metrics["total"]["s"])}</li>
        </ul>
    </li>
    <!-- Keep this li to fix a bad display in the previous li -->
    <li></li>
</ul>
"""

        dialog = QDialog()
        dialog.setWindowTitle(f"Statistiques - {APP_NAME} v{__version__}")
        dialog.setWindowIcon(self.icon)
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.resize(300, 460)

        content = QTextEdit()
        content.setStyleSheet("background-color: #eee; border: none;")
        content.setReadOnly(True)
        content.setHtml(html)

        buttons = QDialogButtonBox()
        buttons.setStandardButtons(QDialogButtonBox.Ok)
        buttons.clicked.connect(dialog.destroy)

        layout = QVBoxLayout()
        layout.addWidget(content)
        layout.addWidget(buttons)
        dialog.setLayout(layout)

        self._dialog = dialog
        self._dialog.show()
        self._dialog.raise_()
