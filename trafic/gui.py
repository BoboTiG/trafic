# coding: utf-8
import sys
from contextlib import suppress
from pathlib import Path

from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QDesktopServices, QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QMenu,
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

        self.db = db_file

        self.tray_icon = SystemTrayIcon(self)
        self.tray_icon.show()

        self.worker = Worker(self, self.db)

    def output(self, msg: str) -> None:
        """Change the system tray tooltip."""
        self.tray_icon.setToolTip(msg)


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

    def exit(self) -> None:
        """Quit the current application."""
        self.hide()
        self.app.worker.need_to_run = False
        self.app.worker.thr.join()
        self.app.exit()

    def open_file(self) -> None:
        """Open the metrics database file.  It requires a SQLite database browser."""
        url = QUrl.fromLocalFile(self.app.db)
        QDesktopServices.openUrl(url)

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
