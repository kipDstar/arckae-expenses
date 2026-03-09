import os
import sys

from streamlit.web import bootstrap


def get_app_path() -> str:
    if getattr(sys, "frozen", False):
        base_dir = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "app.py")


def main() -> None:
    script_path = get_app_path()
    bootstrap.run(script_path, "", [], flag_options={})


if __name__ == "__main__":
    main()

