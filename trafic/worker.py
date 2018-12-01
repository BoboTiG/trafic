# coding: utf-8
import threading
import time
from contextlib import suppress
from typing import TYPE_CHECKING

from .constants import DELAY
from .trafic import trafic
from .utils import tooltip, update

if TYPE_CHECKING:
    from .console import Application  # noqa


class Worker:
    def __init__(self, app: "Application", db_file: str):
        self.db = db_file
        self.app = app

        self.cls = trafic()
        self.need_to_run = True

        self.thr = threading.Thread(target=self.run)
        self.thr.start()

    def run(self) -> None:
        """The endless loop that will do the work."""
        last_received = last_sent = cumul_rec = cumul_sen = 0
        first_run = True

        while self.need_to_run:
            with suppress(Exception):
                rec, sen = self.cls.metrics()

                if first_run:
                    # We want to record metrics only when the application is running,
                    # so the first time we skip metrics as on GNU/Linux we will have
                    # huge data and it will blow up statistics.
                    first_run = False
                    self.app.output(f"Enregistrement en cours ... ({DELAY // 60} min)")
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
                    update(self.db, diff_rec, diff_sen)
                    self.app.output(tooltip(cumul_rec, cumul_sen))

                last_received, last_sent = rec, sen

            self.wait()

    def wait(self) -> None:
        """"""
        for _ in range(DELAY):
            if not self.need_to_run:
                break
            time.sleep(1)
