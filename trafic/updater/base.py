"""
Retrieve data metrics from all network adaptator.

This module is maintained by Mickaël Schoentgen <contact@tiger-222.fr>.

You can always get the latest version of this module at:
    https://github.com/BoboTiG/trafic
If that URL should fail, try contacting the author.
"""
import os
import uuid
from abc import abstractmethod
from tempfile import gettempdir
from typing import Any, Callable, Dict, List

import requests

from .utils import get_update_status
from ..constants import UPDATE_URL
from ..utils import sizeof_fmt


class BaseUpdater:
    """ Updater class for frozen application. """

    def __init__(self, callback: Callable[[str], None], url: str = "") -> None:
        # The function that will be passed a string argument to ease following the update process
        self.callback = callback
        self.url = url or UPDATE_URL

        self.versions: List[Dict[str, Any]] = []
        self.chunk_size = 8192

    #
    # Public methods that can be overrided
    #

    @abstractmethod
    def install(self, filename: str) -> None:
        """
        Install the new version.
        Uninstallation of the old one or any actions needed to install
        the new one has to be handled by this method.
        """

    def update(self, version: str) -> None:
        self.callback(f"Processus de mise à jour vers la version {version}")
        self._install(version, self._download(version))

    #
    # Private methods, should not try to override
    #

    def _download(self, version: str) -> str:
        """ Download a given version to a temporary file. """

        url = ""
        name = ""
        total_size = ""
        for version_info in self.versions:
            print(version_info["name"], version)
            if version_info["name"] == version:
                asset = version_info["assets"][0]
                url = asset["browser_download_url"]
                name = asset["name"]
                total_size = sizeof_fmt(asset["size"], suffix="o")
                break

        path = os.path.join(gettempdir(), uuid.uuid4().hex + "_" + name)

        self.callback(f"Téléchargement de la version {version} dans {path}")

        with requests.get(url, stream=True) as req, open(path, "wb") as tmp:
            for n, chunk in enumerate(req.iter_content(self.chunk_size), 1):
                tmp.write(chunk)
                size = sizeof_fmt(n * self.chunk_size, suffix="o")
                self.callback(f"Mise à jour : téléchargé {size} sur {total_size}")

            # Force write of file to disk
            tmp.flush()
            os.fsync(tmp.fileno())

        return path

    def _fetch_versions(self) -> None:
        """ Fetch available versions. It sets `self.versions` on success. """
        with requests.get(self.url) as resp:
            resp.raise_for_status()
            self.versions = resp.json()

    def _install(self, version: str, filename: str) -> None:
        """
        OS-specific method to install the new version.
        It must take care of uninstalling the current one.
        """
        self.callback(f"Installation de la version {version}")
        self.install(filename)

    def check(self, version: str) -> None:
        """ Retrieve available versions and install an eventual found candidate. """
        try:
            self._fetch_versions()
            new_version = get_update_status(version, self.versions)
            if new_version:
                self.callback(f"Nouvelle version disponible : {new_version}")
                self.update(new_version)
            else:
                self.callback("Vous utilisez la version la plus récente !")
        except Exception as exc:
            self.callback(f"Erreur de MàJ automatique : {exc}")
