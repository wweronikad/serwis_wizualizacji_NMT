import os
import sys
from pathlib import Path
import requests

BASE_URL = os.environ.get("SERWER_URL", "http://127.0.0.1:8001")
DANE_DIR = Path(__file__).resolve().parent / "dane"
WYNIKI_DIR = Path(__file__).resolve().parent / "wyniki"
DEM_EXTENSIONS = {".tif", ".tiff", ".asc", ".adf", ".img", ".hdr"}


def list_dem_files():
    if not DANE_DIR.is_dir():
        return []
    return [path for path in DANE_DIR.iterdir() if path.is_file() and path.suffix.lower() in DEM_EXTENSIONS]


def process_one_file(input_path: Path, output_path: Path, output_format: str, title: str = "") -> bool:
    try:
        with open(input_path, "rb") as file:
            response = requests.post(
                f"{BASE_URL}/process",
                files={"file": (input_path.name, file, "application/octet-stream")},
                data={
                    "title": title or output_path.stem,
                    "output_format": output_format
                },
                timeout=120
            )
    except requests.exceptions.ConnectionError:
        print(f"Błąd: Brak połączenia z {BASE_URL}. Uruchom serwer (python serwer.py).", file=sys.stderr)
        return False
    except requests.exceptions.Timeout:
        print("Błąd: Przekroczono limit czasu.", file=sys.stderr)
        return False
    except OSError as error:
        print(f"Błąd pliku: {error}", file=sys.stderr)
        return False
    
    if response.status_code != 200:
        try:
            error_data = response.json()
            print(f"Błąd serwera: {error_data.get('error', 'Nieznany błąd')}", file=sys.stderr)
        except:
            print(f"Błąd serwera ({response.status_code}): {response.text[:300]}", file=sys.stderr)
        return False
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)
    return True


def run_interactive() -> int:
    dem_files = list_dem_files()
    file_count = len(dem_files)
    print(f"W katalogu 'dane' jest {file_count} plików NMT.")
    if not file_count:
        print("Dodaj pliki NMT do katalogu 'dane'.")
        return 0
    for index, file_path in enumerate(dem_files, 1):
        print(f"  {index}. {file_path.name}")
    print()
    WYNIKI_DIR.mkdir(parents=True, exist_ok=True)
    success_count = 0
    for file_path in dem_files:
        print(f"Plik: {file_path.name}")
        title = input("  Tytuł: ").strip() or file_path.stem
        output_format = input("  Format (png/jpg/jpeg): ").strip().lower() or "png"
        if output_format not in ("png", "jpg", "jpeg"):
            output_format = "png"
        safe_filename = "".join(char for char in title if char.isalnum() or char in " _-").strip() or file_path.stem
        output_path = WYNIKI_DIR / f"{safe_filename}.{output_format}"
        print(f"  Zapis: {output_path}")
        if process_one_file(file_path, output_path, output_format, title):
            print(f"  OK: {output_path}")
            success_count += 1
        else:
            print("  Błąd.", file=sys.stderr)
        print()
    print(f"Gotowe: {success_count}/{file_count} plików w 'wyniki'.")
    return 0 if success_count == file_count else 2


def run_single_file(input_file: str, output_file: str) -> int:
    input_path = Path(input_file)
    if not input_path.is_file():
        print(f"Błąd: Brak pliku {input_file}", file=sys.stderr)
        return 1
    output_path = Path(output_file)
    output_format = output_path.suffix.lstrip(".").lower() or "png"
    if output_format not in ("png", "jpg", "jpeg"):
        output_format = "png"
    print(f"Wysyłanie {input_path}…")
    if not process_one_file(input_path, output_path, output_format, output_path.stem):
        return 2
    print(f"Zapisano: {output_path}")
    return 0


def main():
    arguments = sys.argv[1:]
    if not arguments:
        sys.exit(run_interactive())
    input_file, output_file = None, None
    index = 0
    while index < len(arguments):
        if arguments[index] == "--input" and index + 1 < len(arguments):
            input_file, index = arguments[index + 1], index + 2
        elif arguments[index] == "--output" and index + 1 < len(arguments):
            output_file, index = arguments[index + 1], index + 2
        else:
            index += 1
    if input_file and output_file:
        sys.exit(run_single_file(input_file, output_file))
    sys.exit(1)


if __name__ == "__main__":
    main()
