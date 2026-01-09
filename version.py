# version.py
"""
Informacje o wersji aplikacji
"""

__version__ = "2.1.0"
__version_info__ = (2, 1, 0)
__build_date__ = "2026-01-06"  # Dzisiejsza data
__author__ = "@AJPerkele"
__app_name__ = "System Magazynowo-Sprzedażowy"
__license__ = "GNU General Public License v3.0"

def get_version():
    """Zwraca pełną informację o wersji"""
    return {
        "version": __version__,
        "version_info": __version_info__,
        "build_date": __build_date__,
        "author": __author__,
        "app_name": __app_name__,
        "license": __license__
    }

def display_version():
    """Wyświetla informację o wersji"""
    info = get_version()
    print(f"{info['app_name']} v{info['version']}")
    print(f"Data budowy: {info['build_date']}")
    print(f"Autor: {info['author']}")
    print(f"Licencja: {info['license']}")
    
    # Dodatkowe informacje
    print(f"\nFunkcje w tej wersji:")
    print("- Historia rachunków z możliwością usuwania")
    print("- Poprawione polskie znaki w PDF")
    print("- Inteligentne liczenie transakcji")
    print("- Pełna ewidencja dla US")
    print("- Konfiguracja wyglądu rachunków")
    print("- Resetowanie numeracji faktur")
    
    return info

if __name__ == "__main__":
    display_version()
