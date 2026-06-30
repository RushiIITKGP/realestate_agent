from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from main import import_listings

cities = [
    ("Austin", "TX"),
    ("Dallas", "TX"),
    ("Houston", "TX"),
]

for i, (city, state) in enumerate(cities):
    result = import_listings(city, state, limit=100, replace=(i == 0))
    print(f"{city}, {state}: {result['listings']} listings, {result['embedded']} embedded")