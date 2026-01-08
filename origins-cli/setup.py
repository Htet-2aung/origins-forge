from setuptools import setup

setup(
    name="origins-cli",
    version="1.0",
    py_modules=["main"],
    install_requires=[
        "typer[all]",
        "rich",
        "shellingham",
    ],
    entry_points={
        "console_scripts": [
            "origins=main:app",  # This maps the command 'origins' to your app
        ],
    },
)