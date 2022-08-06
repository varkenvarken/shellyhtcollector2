from setuptools import setup

from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="htcollector",
    version="0.0.2",
    description="Tools to log updates from Shelly HT devices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://varkenvarken.github.io/shellyhtcollector2/",
    author="varkenvarken",
    author_email="test@example.com",
    license="GPLv3",
    packages=["shellyhtcollector"],
    python_requires=">=3.8",
    install_requires=[
        "mariadb",
        "python-dateutil",
    ],
    zip_safe=False,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
)
