# coding: utf-8
"""
Retrieve data metrics from all network adaptator.

The script will log received and sent bytes.
There is also a little systray icon with a counter.

Mickaël 'Tiger-222' Schoentgen
Created: 2018-08-23
Updated: check the Git history

Icon:
    https://commons.wikimedia.org/wiki/File:Transfer-down_up.svg -> trafic.svg
"""

__version__ = "0.1.0"

import logging
import re
import sys
import threading
import time
from contextlib import suppress
from dataclasses import dataclass
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Tuple

import delegator
from PyQt5.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon
from PyQt5.QtGui import QIcon

# from tendo.singleton import SingleInstance, SingleInstanceException


log = logging.getLogger(__name__)


class Application(QApplication):

    need_to_run = True

    def __init__(self, folder: Path):
        QApplication.__init__(self, [])

        self.create_timed_rotating_log(folder)
        self.tray_icon = SystemTrayIcon(self)
        self.tray_icon.show()
        self.cls = (TraficNonWindows, TraficWindows)[sys.platform.startswith("win")]()
        self.thr = threading.Thread(target=self.run, args=(self,))
        self.thr.start()

    def create_timed_rotating_log(self, folder: Path) -> None:
        """Instanciate the hourly rotated logger."""
        handler = TimedRotatingFileHandler(folder / "statistics.log", when="midnight")
        log.addHandler(handler)
        log.setLevel(logging.INFO)

    def run(self, app: "Application") -> None:
        """The endless loop that will do the work."""
        last_received, last_sent = 0, 0
        cumul_rec, cumul_sen = 0, 0
        cls = app.cls

        while app.need_to_run:
            with suppress(Exception):
                rec, sen = cls.get_stats()
                if last_received < rec:
                    cls.total_received = rec + cumul_rec
                    cls.total_sent = sen + cumul_sen
                else:
                    cumul_rec += last_received
                    cumul_sen += last_sent

                last_received, last_sent = rec, sen
                app.tray_icon.setToolTip(
                    f"↓↓ {cls.bytes_to_mb(cls.total_received)} Mo -"
                    f" ↑ {cls.bytes_to_mb(cls.total_sent)} Mo"
                )

            time.sleep(60)  # 1 minute


class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, app, parent=None):
        QSystemTrayIcon.__init__(self, parent=parent)

        self.app = app

        icon = Path(getattr(sys, "_MEIPASS", ".")) / "trafic.svg"
        self.setIcon(QIcon(str(icon)))

        style = QApplication.style()
        menu = QMenu(parent)
        action = menu.addAction(
            style.standardIcon(QStyle.SP_DialogCloseButton), "Quitter"
        )
        action.triggered.connect(self.exit)
        self.setContextMenu(menu)

    def exit(self) -> None:
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

        log.info(f"{received} {sent}")
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
    try:
        return app.exec_()
    except KeyboardInterrupt:
        app.need_to_run = False
        app.thr.join()
        return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
