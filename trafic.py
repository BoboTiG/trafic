# coding: utf-8
"""
Retrieve data metrics from all network adaptator.

The script will save received and sent bytes in a SQLite3 database.
There is also a little systray icon with a counter.

Mickaël 'Tiger-222' Schoentgen
Created: 2018-08-23
Updated: check the Git history

Icon:
    https://commons.wikimedia.org/wiki/File:Transfer-down_up.svg -> trafic.svg
"""

__version__ = "0.2.0"

import re
import sys
import threading
import time
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from sqlite3 import connect
from typing import Dict, List, Tuple

import delegator
from PyQt5.QtCore import Qt, QUrl
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
from PyQt5.QtGui import QDesktopServices, QIcon

# from tendo.singleton import SingleInstance, SingleInstanceException


# Constants
APP_NAME = "Trafic"
ICON_DOWN = "↓"
ICON_UP = "↑"
ICON_SEP = "•"
COLOR_DOWN = "red"
COLOR_UP = "green"


class Application(QApplication):

    delay = 60 * 5  # 5 minutes
    need_to_run = True

    def __init__(self, folder: Path):
        QApplication.__init__(self, [])

        # sqlite3.connect() does not allow WindowsPath, but PosixPath is OK ...
        # So using str().
        db_file = folder / "statistics.db"
        self.db = str(db_file)
        if not db_file.is_file():
            self.create_db()

        self.tray_icon = SystemTrayIcon(self)
        self.tray_icon.show()
        self.cls = (TraficNonWindows, TraficWindows)[sys.platform.startswith("win")]()
        self.thr = threading.Thread(target=self.run, args=(self,))
        self.thr.start()

    def create_db(self) -> None:
        """Create the metrics database."""
        with connect(self.db) as conn:
            conn.cursor().execute(
                "CREATE TABLE IF NOT EXISTS Statistics ("
                "    run_at   DATETIME,"
                "    received INTEGER,"
                "    sent     INTEGER,"
                "    PRIMARY KEY (run_at)"
                ")"
            )

    def get(self, days: int = 0) -> List[Tuple[str, int, int]]:
        """Get metrics from the database."""
        sql = (
            "  SELECT strftime('%Y-%m-%d', run_at) d, SUM(received), SUM(sent)"
            "    FROM Statistics "
            "GROUP BY d "
            "ORDER BY d DESC"
        )
        if days > 0:
            sql += f" LIMIT {days}"

        with connect(self.db) as conn:
            return conn.cursor().execute(sql).fetchall()

    def update(self, received: int, sent: int) -> None:
        """Save metrics in the database."""
        run_at = datetime.now().replace(second=0, microsecond=0)

        with connect(self.db) as conn:
            conn.cursor().execute(
                "INSERT OR IGNORE INTO Statistics(run_at, received, sent)"
                "               VALUES (?, ?, ?)",
                (run_at, received, sent),
            )

    def run(self, app: "Application") -> None:
        """The endless loop that will do the work."""
        last_received = last_sent = cumul_rec = cumul_sen = 0
        first_run = True

        while app.need_to_run:
            with suppress(Exception):
                rec, sen = app.cls.metrics()

                if first_run:
                    # We want to record metrics only when the application is running,
                    # so the first time we skip metrics as on GNU/Linux we will have
                    # huge data and it will blow up statistics.
                    first_run = False
                    app.tray_icon.setToolTip(
                        f"Enregistrement en cours ... ({app.delay // 60} min)"
                    )
                else:
                    if rec >= last_received and sen >= last_sent:
                        # Susbstract new values to old ones to keep revelant values.
                        diff_rec = rec - last_received
                        diff_sen = sen - last_sent
                    else:
                        # On Windows, when the network adaptater is re-enabled,
                        # on session reload or on a computer crash, adaptater
                        # statistics are resetted.
                        diff_rec, diff_sen = rec, sen

                    cumul_rec += diff_rec
                    cumul_sen += diff_sen
                    app.update(diff_rec, diff_sen)
                    app.tray_icon.setToolTip(app.tooltip(cumul_rec, cumul_sen))

                last_received, last_sent = rec, sen

            for _ in range(app.delay):
                if not app.need_to_run:
                    break
                time.sleep(1)

    @staticmethod
    def tooltip(received: int, sent: int) -> str:
        """Return a pretty line of counter values."""
        return f"{ICON_DOWN} {sizeof_fmt(received)} {ICON_SEP} {ICON_UP} {sizeof_fmt(sent)}"


class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, app: Application) -> None:
        QSystemTrayIcon.__init__(self)

        self.app = app

        icon = Path(getattr(sys, "_MEIPASS", ".")) / "trafic.svg"
        self.icon = QIcon(str(icon))
        self.setIcon(self.icon)

        self.create_menu()
        self._dialog = None

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
        self.app.need_to_run = False
        self.app.thr.join()
        self.app.exit()

    def get_stats(self) -> Dict[str, Dict[str, int]]:
        """Retreive statistics and pre-format them into a dict."""
        filtered_metrics = {
            "1d": {"r": 0, "s": 0},
            "7d": {"r": 0, "s": 0},
            "30d": {"r": 0, "s": 0},
            "total": {"r": 0, "s": 0, "d": 0},
        }
        for n, (_, received, sent) in enumerate(self.app.get()):
            if n < 1:
                filtered_metrics["1d"]["r"] += received
                filtered_metrics["1d"]["s"] += sent
                filtered_metrics["7d"]["r"] += received
                filtered_metrics["7d"]["s"] += sent
                filtered_metrics["30d"]["r"] += received
                filtered_metrics["30d"]["s"] += sent
            elif n < 7:
                filtered_metrics["7d"]["r"] += received
                filtered_metrics["7d"]["s"] += sent
                filtered_metrics["30d"]["r"] += received
                filtered_metrics["30d"]["s"] += sent
            elif n < 30:
                filtered_metrics["30d"]["r"] += received
                filtered_metrics["30d"]["s"] += sent

            filtered_metrics["total"]["r"] += received
            filtered_metrics["total"]["s"] += sent
            filtered_metrics["total"]["d"] += 1

        return filtered_metrics

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

        metrics = self.get_stats()
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


@dataclass
class Trafic:
    """Parent class for all OSes."""

    def metrics(self) -> Tuple[int, int]:
        """Retreive bytes received and sent."""
        cmd = delegator.run(self.cmd, binary=True)
        received = sent = 0

        # In case there are more than one adaptator, we accumulate metrics
        for rec, sen in re.findall(self.pattern, cmd.out):
            received += int(rec)
            sent += int(sen)

        return received, sent


@dataclass
class TraficNonWindows(Trafic):
    """Targetting GNU/Linux and macOS."""

    cmd = "netstat -s"
    pattern = re.compile(br"\s+InOctets: (\d+)\n\s+OutOctets: (\d+)")


@dataclass
class TraficWindows(Trafic):
    """Targetting Windows."""

    cmd = ["netstat", "-e", "-a"]
    pattern = re.compile(br"(?:Bytes|Octets)\s+(\d+)\s+(\d+)")


def sizeof_fmt(num: int, suffix: str = "o") -> str:
    """
    Human readable version of file size.
    Supports:
        - all currently known binary prefixes (https://en.wikipedia.org/wiki/Binary_prefix)
        - negative and positive numbers
        - numbers larger than 1,000 Yobibytes
        - arbitrary units

    Examples:

        >>> sizeof_fmt(168963795964)
        "157.4 Gio"
        >>> sizeof_fmt(168963795964, suffix="B")
        "157.4 GiB"

    Source: https://stackoverflow.com/a/1094933/1117028
    """
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f} Yi{suffix}"


def main() -> int:
    """Main logic."""

    # Log and lock files folder
    folder = Path("~/trafic").expanduser()
    if not folder.is_dir():
        folder.mkdir()

    # Allow only one instance
    """
    TODO: https://github.com/pycontribs/tendo/issues/32
    lockfile = folder / "trafic.lock"
    try:
        me = SingleInstance(lockfile=lockfile)
        print(me)
    except SingleInstanceException:
        return 1
    """

    # C'est parti mon kiki !
    app = Application(folder)
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
