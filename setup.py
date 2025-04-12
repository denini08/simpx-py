from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="simpx-py",
    version="0.1.0",
    author="FailSpy",
    description="A Pythonic framework for creating SimpleX chat bots",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/FailSpy/simpx-py",
    project_urls={
        "Bug Tracker": "https://github.com/FailSpy/simpx-py/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "websockets",
        "qrcode"
    ],
)
