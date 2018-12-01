# coding: utf-8
import re
from typing import Tuple

from dataclasses import dataclass

import delegator

from .constants import WINDOWS


@dataclass
class Trafic:
    """Parent class for all OSes."""

    def metrics(self) -> Tuple[int, int]:
        """Retreive bytes received and sent."""
        cmd = delegator.run(self.cmd, binary=True)  # type: ignore
        received = sent = 0

        # In case there are more than one adaptator, we accumulate metrics
        for rec, sen in re.findall(self.pattern, cmd.out):  # type: ignore
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


def trafic() -> Trafic:
    """Factory."""
    return (TraficNonWindows, TraficWindows)[WINDOWS]()
