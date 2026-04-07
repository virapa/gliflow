from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from src.app import GliFlowApp

if __name__ == "__main__":
    GliFlowApp().run()
