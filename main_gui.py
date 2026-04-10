#!/usr/bin/env python3
"""GUI-Einstiegspunkt für den BingX BTC Trader.

Startet die grafische Oberfläche. Der CLI-Modus bleibt über main.py verfügbar.

Verwendung:
    python main_gui.py
"""

from trader.config import Settings
from trader.gui.app import TradingApp


if __name__ == "__main__":
    settings = Settings.from_env()
    app = TradingApp(settings)
    app.mainloop()
