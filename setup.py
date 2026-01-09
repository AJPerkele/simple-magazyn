from setuptools import setup, find_packages
from version import __version__

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="system-magazynowy",
    version=__version__,
    author="Twój Zespół",
    author_email="twój@email.com",
    description="System magazynowo-sprzedażowy z ewidencją uproszczoną",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/twoj-username/magazyn-sprzedaz",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "PySide6>=6.5.0",
        "reportlab>=4.0.0",
        "requests>=2.31.0",
        "openpyxl>=3.1.0",
    ],
    entry_points={
        "console_scripts": [
            "magazyn-sprzedaz=app:main",
        ],
    },
)
