from __future__ import annotations

import sys


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("Missing dependency: PySide6. Run `pip install -r requirements.txt` first.")
        return 1

    from infra.logger import setup_logger
    from ui.main_window import MainWindow

    setup_logger()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
