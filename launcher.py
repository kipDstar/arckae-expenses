import subprocess
import sys


def main() -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app.py",
        ],
        check=False,
    )


if __name__ == "__main__":
    main()

