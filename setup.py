from setuptools import setup, find_packages

setup(
    name="xovis-sdk",
    version="0.0.1",
    description="Unofficial community SDK for Xovis Hardware and HUB",
    author="Xovis Open SDK Team",
    author_email="xovis.sdk@proton.me",
    url="https://github.com/xovis-sdk-team/xovis-sdk",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)