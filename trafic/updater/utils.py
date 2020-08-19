"""
Retrieve data metrics from all network adaptator.

This module is maintained by Mickaël Schoentgen <contact@tiger-222.fr>.

You can always get the latest version of this module at:
    https://github.com/BoboTiG/trafic
If that URL should fail, try contacting the author.
"""
from distutils.version import StrictVersion
from typing import Any, Dict, List

__all__ = ("get_update_status",)

Version = Dict[str, Any]
Versions = List[Version]


def get_latest_version(versions: Versions) -> str:
    """ Get the most recent version. """
    versions_currated = [version["name"] for version in versions]
    highest = str(max(map(StrictVersion, versions_currated)))
    return highest  # ᕦ(ò_óˇ)ᕤ


def get_update_status(current_version: str, versions: Versions) -> str:
    """Given a version, determine the definitive status of the application."""
    if not versions:
        return ""

    latest = get_latest_version(versions)
    if not latest or StrictVersion(latest) <= StrictVersion(current_version):
        return ""

    # StrictVersion.__str__() will strip the leading ".0", just restore it
    #
    #   >>> StrictVersion("0.2.0")
    #   StrictVersion ('0.2')
    #   >>> str(StrictVersion("0.2.0"))
    #   '0.2'
    #
    if latest.count(".") == 1:
        latest += ".0"

    return latest
