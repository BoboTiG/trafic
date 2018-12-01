# coding: utf-8
from sys import platform

# Application name
APP_NAME = "Trafic"

# Metrics retrieval interval
DELAY = 60 * 5  # 5 minutes

# Icons
ICON_DOWN = "↓"
ICON_SEP = "•"
ICON_UP = "↑"

# Download and upload colors
COLOR_DOWN = "red"
COLOR_UP = "green"

# Running on Windows?
WINDOWS = platform.startswith("win")
