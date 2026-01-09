from setuptools import setup

setup(
    name="origins-forge",
    version="0.2.4",
    py_modules=["main"],
    install_requires=[
        "typer[all]",
        "rich",
        "google-genai",
        "questionary",
        "PyGithub",
    ],
    entry_points={
        "console_scripts": [
            "origins=main:app",
        ],
    },
)
