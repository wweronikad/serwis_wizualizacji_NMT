Serwis Wizualizacji Numerycznego Modelu Terenu
----------------------------------------------

OPIS PROJEKTU

Aplikacja klient-serwer do przetwarzania plików NMT.
Przykładowe dane znajdują się w katalogu 'dane'.
Wyniki zapisywane są w katalogu 'wyniki', przykładowe wyniki znajdują się w katalogu 'wyniki'.
Serwer generuje kolorowe wydruki map z nałożonym cieniowaniem i legendą.
Użytkownik może wybrać tytuł i format (png/jpg).
Tytuł staje się również nazwą pliku wyjściowego.
Jeżeli nie podamy tytułu, zostanie on wygenerowany na podstawie nazwy pliku wejściowego.
Domyślny format to png.

URUCHOMIENIE

1. serwer:
   > python serwer.py

2. klient:

   a) Tryb interaktywny:
      > python klient.py
      - Wyświetla pliki NMT z katalogu 'dane/'
      - Pyta o tytuł i format (png/jpg)
      - Zapisuje wyniki do 'wyniki/'

   b) Tryb pojedynczego pliku:
      > python klient.py --input dane/nazwa_pliku.tif --output wyniki/nazwa_pliku.png

STRUKTURA PROJEKTU

projekt/
├── dane/           - pliki wejściowe NMT
├── wyniki/         - wygenerowane mapy
├── klient.py       - klient
├── serwer.py       - serwer
├── requirements.txt
└── README.txt

FUNKCJE SERWERA

- Kolorowanie według wysokości (gdaldem color-relief)
- Cieniowanie terenu (gdaldem hillshade)
- Legenda z paskiem kolorów (matplotlib)
- Tytuł mapy

KODY WYJŚCIA KLIENTA

0 - sukces
1 - błąd argumentów
2 - błąd serwera lub połączenia

