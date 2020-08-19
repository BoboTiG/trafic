"""
Retrieve data metrics from all network adaptator.

This module is maintained by Mickaël Schoentgen <contact@tiger-222.fr>.

You can always get the latest version of this module at:
    https://github.com/BoboTiG/trafic
If that URL should fail, try contacting the author.
"""
from . import __version__
from .constants import APP_NAME
from .worker import Worker


class Application:
    def __init__(self, db_file: str):
        self.db = db_file

        self.worker = Worker(self, self.db)

    def exec_(self) -> int:
        """Mimic the QApplication;exec_() method."""

        print(f"{APP_NAME} v{__version__}")

        try:
            self.worker.thr.join()
            return 0
        except KeyboardInterrupt:
            self.worker.need_to_run = False
            self.worker.thr.join()
            return 0
        except Exception:
            return 1

    def output(self, msg: str) -> None:
        """Print some text in the console."""
        print(msg)
