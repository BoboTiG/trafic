import sys
from pathlib import Path

# from tendo.singleton import SingleInstance, SingleInstanceException

from trafic.utils import create_db


def main() -> int:
    """Entry point."""

    if sys.version_info < (3, 6):
        raise RuntimeError("Trafic requires Python 3.6+")

    # Database and lock files folder
    folder = Path("~/trafic").expanduser()
    if not folder.is_dir():
        folder.mkdir()

    db_file = folder / "statistics.db"
    if not db_file.is_file():
        # sqlite3.connect() does not allow WindowsPath, but PosixPath is OK ...
        # So using str().
        create_db(str(db_file))

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
    if "--console" in sys.argv:
        from trafic.console import Application
    else:
        from trafic.gui import Application  # type: ignore

    app = Application(str(db_file))
    return app.exec_()


sys.exit((main()))
