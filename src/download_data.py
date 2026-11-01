"""Download full UCI Online Retail dataset. No credentials required."""
from pathlib import Path
from urllib.request import Request, urlopen
import io
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "data" / "raw" / "Online Retail.xlsx"
URL = "https://archive.ics.uci.edu/static/public/352/online+retail.zip"


def main():
    if TARGET.exists():
        print(f"Already downloaded: {TARGET}")
        return
    print("Downloading the original CC BY 4.0 dataset (~23 MB) from UCI...")
    try:
        request = Request(URL, headers={"User-Agent": "Mozilla/5.0 RetailFlow-Educational-Project"})
        with urlopen(request, timeout=120) as response:
            blob = response.read()
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            candidates = [n for n in archive.namelist() if n.lower().endswith(".xlsx")]
            if not candidates:
                raise RuntimeError("ZIP does not contain an XLSX workbook")
            TARGET.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(candidates[0]) as source, TARGET.open("wb") as dest:
                shutil.copyfileobj(source, dest)
        print(f"Saved {TARGET} ({TARGET.stat().st_size / 1e6:.1f} MB)")
    except Exception as exc:
        print("Automatic download failed:", exc)
        print("Manual fallback: https://archive.ics.uci.edu/dataset/352/online+retail")
        print("Download 'Online Retail.xlsx' and place it in data/raw/ then run python src/etl.py")
        raise SystemExit(1) from exc

if __name__ == "__main__":
    main()
