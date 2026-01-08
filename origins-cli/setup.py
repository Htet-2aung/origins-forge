from setuptools import setup

setup(
    name="origins-cli",
    version="3.0",
    py_modules=["main"],
    install_requires=[
        "typer[all]",
        "rich",
        "requests",
        "openai",
    ],
    entry_points={
        "console_scripts": [
            "origins=main:app", 
        ],
    },
)
