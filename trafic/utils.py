"""
Retrieve data metrics from all network adaptator.

This module is maintained by Mickaël Schoentgen <contact@tiger-222.fr>.

You can always get the latest version of this module at:
    https://github.com/BoboTiG/trafic
If that URL should fail, try contacting the author.
"""
from datetime import datetime
from sqlite3 import connect
from typing import Dict, List, Tuple

from psutil import net_io_counters

from .constants import ICON_DOWN, ICON_SEP, ICON_UP


def create_db(db: str) -> None:
    """Create the metrics database."""
    with connect(db) as conn:
        conn.cursor().execute(
            "CREATE TABLE IF NOT EXISTS Statistics ("
            "    run_at   DATETIME,"
            "    received INTEGER,"
            "    sent     INTEGER,"
            "    PRIMARY KEY (run_at)"
            ")"
        )


def get(db: str, days: int = 0) -> List[Tuple[str, int, int]]:
    """Get metrics from the database."""
    sql = (
        "  SELECT strftime('%Y-%m-%d', run_at) d, SUM(received), SUM(sent)"
        "    FROM Statistics "
        "GROUP BY d "
        "ORDER BY d DESC"
    )
    if days > 0:
        sql += f" LIMIT {days}"

    with connect(db) as conn:
        return conn.cursor().execute(sql).fetchall()


def update(db: str, received: int, sent: int) -> None:
    """Save metrics in the database."""
    run_at = datetime.now().replace(second=0, microsecond=0)

    with connect(db) as conn:
        conn.cursor().execute(
            "INSERT OR IGNORE INTO Statistics(run_at, received, sent)"
            "               VALUES (?, ?, ?)",
            (run_at, received, sent),
        )


def tooltip(received: int, sent: int) -> str:
    """Return a pretty line of counter values."""
    return f"{ICON_DOWN} {sizeof_fmt(received)} {ICON_SEP} {ICON_UP} {sizeof_fmt(sent)}"


def metrics() -> Tuple[int, int]:
    """Retreive bytes received and sent."""
    stats = net_io_counters(nowrap=True)
    return stats.bytes_recv, stats.bytes_sent


def get_stats(db: str) -> Dict[str, Dict[str, int]]:
    """Retreive statistics and pre-format them into a dict."""
    filtered_metrics = {
        "1d": {"r": 0, "s": 0},
        "7d": {"r": 0, "s": 0},
        "30d": {"r": 0, "s": 0},
        "total": {"r": 0, "s": 0, "d": 0},
    }
    for n, (_, received, sent) in enumerate(get(db)):
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
    val = float(num)
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(val) < 1024.0:
            return f"{val:3.1f} {unit}{suffix}"
        val /= 1024.0
    return f"{val:.1f} Yi{suffix}"


def display_stats(db: str):
    """Print statistics in the terminal."""

    metrics = get_stats(db)
    text = f"""
Statistiques Basiques
---------------------

Aujourd'hui :
    {ICON_DOWN} {sizeof_fmt(metrics["1d"]["r"])}
    {ICON_UP} {sizeof_fmt(metrics["1d"]["s"])}

Ces 7 derniers jours :
    {ICON_DOWN} {sizeof_fmt(metrics["7d"]["r"])}
    {ICON_UP} {sizeof_fmt(metrics["7d"]["s"])}

Ces 30 derniers jours :
    {ICON_DOWN} {sizeof_fmt(metrics["30d"]["r"])}
    {ICON_UP} {sizeof_fmt(metrics["30d"]["s"])}

TOTAL ({metrics["total"]["d"]} jours) :
    {ICON_DOWN} {sizeof_fmt(metrics["total"]["r"])}
    {ICON_UP} {sizeof_fmt(metrics["total"]["s"])}
"""
    print(text.lstrip())
