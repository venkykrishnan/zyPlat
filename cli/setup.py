from setuptools import setup, find_packages

setup(
    name="zyplat-cli",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.0",
        "requests>=2.31.0",
        "rich>=13.7.0",
    ],
    entry_points={
        "console_scripts": [
            "zyplat=zyplat_cli.main:cli",
        ],
    },
    python_requires=">=3.11",
)
