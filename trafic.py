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

__version__ = "0.1.0"

import re
import sys
import threading
import time
from contextlib import suppress
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from sqlite3 import connect, OperationalError
from typing import Tuple

import delegator
from PyQt5.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon
from PyQt5.QtGui import QIcon

# from tendo.singleton import SingleInstance, SingleInstanceException


class Application(QApplication):

    need_to_run = True

    def __init__(self, folder: Path):
        QApplication.__init__(self, [])

        # sqlite3.connect() does not allow WindowsPath, but PosixPath is OK ...
        # So using str().
        self.db = str(folder / "statistics.db")

        self.tray_icon = SystemTrayIcon(self)
        self.tray_icon.show()
        self.cls = (TraficNonWindows, TraficWindows)[sys.platform.startswith("win")]()
        self.thr = threading.Thread(target=self.run, args=(self,))
        self.thr.start()

    def get_today_stats(self) -> Tuple[int, int]:
        """Get current day statistics from the database."""
        today = date.today()
        defaults = 0, 0

        with suppress(OperationalError), connect(self.db) as conn:
            cur = conn.cursor()
            return (
                cur.execute(
                    "SELECT received, sent FROM Statistics WHERE day = ?", (today,)
                ).fetchone()
                or defaults
            )
        return defaults

    def update_stats(self, received: int, sent: int) -> None:
        """Save statistics in the database."""
        today = date.today()

        with connect(self.db) as conn:
            cur = conn.cursor()

            # Create the schema the first time
            cur.execute(
                "CREATE TABLE IF NOT EXISTS Statistics ("
                "    day      DATETIME NOT NULL,"
                "    received INTEGER DEFAULT 0,"
                "    sent     INTEGER DEFAULT 0,"
                "    PRIMARY KEY (day)"
                ")"
            )

            # Insert or update values
            cur.execute(
                "INSERT OR IGNORE INTO Statistics(day, received, sent)"
                "               VALUES (?, ?, ?)",
                (today, received, sent),
            )
            cur.execute(
                "UPDATE Statistics SET received = ?, sent = ? WHERE day = ?",
                (received, sent, today),
            )
            conn.commit()

    def run(self, app: "Application") -> None:
        """The endless loop that will do the work."""
        last_received, last_sent = app.get_today_stats()
        cumul_rec, cumul_sen = 0, 0
        cls = app.cls

        if last_received or last_sent:
            cls.total_received = last_received
            cls.total_sent = last_sent

        app.tray_icon.setToolTip(cls.tooltip)

        while app.need_to_run:
            with suppress(Exception):
                rec, sen = cls.get_stats()
                if last_received < rec or last_sent < sen:
                    cls.total_received = rec + cumul_rec
                    cls.total_sent = sen + cumul_sen
                    app.update_stats(cls.total_received, cls.total_sent)
                    app.tray_icon.setToolTip(cls.tooltip)
                else:
                    # On Windows, when the network adaptater is re-enabled,
                    # on session reload or on a computer crash, adaptater
                    # statistics are resetted.
                    cumul_rec += last_received
                    cumul_sen += last_sent

                last_received, last_sent = rec, sen

            for _ in range(60 * 15):  # 15 minutes
                if not app.need_to_run:
                    break
                time.sleep(1)


class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, app: Application) -> None:
        QSystemTrayIcon.__init__(self)

        self.app = app

        icon = Path(getattr(sys, "_MEIPASS", ".")) / "trafic.svg"
        self.icon = QIcon(str(icon))
        self.setIcon(self.icon)

        self.create_menu()

    def create_menu(self) -> None:
        """Create the context menu."""
        menu = QMenu()
        style = QApplication.style()

        for icon, label, func in (
            # (self.icon, "Statistiques", self.msgbox),
            (style.standardIcon(QStyle.SP_DialogCloseButton), "Quitter", self.exit),
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


@dataclass
class Trafic:
    """Parent class for all OSes. Default values targetting Windows."""

    total_received = 0
    total_sent = 0

    def bytes_to_mb(self, value: int) -> float:
        """Convert bytes to Mb."""
        return int(value / 1024 / 1024)

    def get_stats(self) -> Tuple[int, int]:
        """Simple logger for bytes received and sent."""
        cmd = delegator.run(self.cmd)
        received, sent = 0, 0

        # In case there are more than one adaptator, we accumulate metrics
        for rec, sen in re.findall(self.pattern, cmd.out):
            received += int(rec)
            sent += int(sen)

        return received, sent

    @property
    def tooltip(self) -> str:
        """Return a pretty line of counter values."""
        return (
            f"↓↓ {self.bytes_to_mb(self.total_received)} Mo -"
            f" ↑ {self.bytes_to_mb(self.total_sent)} Mo"
        )


@dataclass
class TraficNonWindows(Trafic):
    """Targetting GNU/Linux and macOS."""

    cmd = "netstat -s"
    pattern = re.compile(r"\s+InOctets: (\d+)\n\s+OutOctets: (\d+)")


@dataclass
class TraficWindows(Trafic):
    """Targetting Windows."""

    cmd = ["netstat", "-e"]
    pattern = re.compile(r"(?:Bytes|Octets)\s+(\d+)\s+(\d+)")


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
