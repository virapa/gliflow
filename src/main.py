from pathlib import Path
from dotenv import load_dotenv

from .app import GliFlowApp

# Load .env from project root (next to src/)
load_dotenv(Path(__file__).parent.parent / ".env")


def main() -> None:
    app = GliFlowApp()
    app.run()


if __name__ == "__main__":
    main()
