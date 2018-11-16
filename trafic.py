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
from datetime import datetime
from pathlib import Path
from sqlite3 import connect
from typing import Tuple

import delegator
from PyQt5.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon
from PyQt5.QtGui import QIcon

# from tendo.singleton import SingleInstance, SingleInstanceException


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

    def update_stats(self, received: int, sent: int) -> None:
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
                    diff_rec = diff_sen = 0
                elif rec >= last_received and sen >= last_sent:
                    diff_rec = rec - last_received
                    diff_sen = sen - last_sent
                else:
                    # On Windows, when the network adaptater is re-enabled,
                    # on session reload or on a computer crash, adaptater
                    # statistics are resetted.
                    diff_rec, diff_sen = rec, sen

                cumul_rec += diff_rec
                cumul_sen += diff_sen
                last_received, last_sent = rec, sen

                if first_run:
                    first_run = False
                    app.tray_icon.setToolTip(
                        f"Enregistrement en cours ({app.delay // 60} min)"
                    )
                else:
                    app.update_stats(diff_rec, diff_sen)
                    app.tray_icon.setToolTip(app.tooltip(cumul_rec, cumul_sen))

            for _ in range(app.delay):
                if not app.need_to_run:
                    break
                time.sleep(1)

    @staticmethod
    def tooltip(received: int, sent: int) -> str:
        """Return a pretty line of counter values."""
        return f"↓↓ {bytes_to_mb(received)} Mo - ↑ {bytes_to_mb(sent)} Mo"


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
    """Parent class for all OSes."""

    def metrics(self) -> Tuple[int, int]:
        """Retreive bytes received and sent."""
        cmd = delegator.run(self.cmd)
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
    pattern = re.compile(r"\s+InOctets: (\d+)\n\s+OutOctets: (\d+)")


@dataclass
class TraficWindows(Trafic):
    """Targetting Windows."""

    cmd = ["netstat", "-e"]
    pattern = re.compile(r"(?:Bytes|Octets)\s+(\d+)\s+(\d+)")


def bytes_to_mb(value: int) -> float:
    """Convert bytes to Mib."""
    return int(value / 1024 / 1024)


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
