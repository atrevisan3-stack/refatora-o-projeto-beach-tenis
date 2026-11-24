"""Ponto de entrada: ``python -m dante_squash``."""

import os

from dante_squash.composition import Application

if __name__ == "__main__":
    Application(os.environ).run()
