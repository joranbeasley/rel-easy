##### Created By releasy ##########################
import setuptools
from releasy.version import __version__
setuptools.setup(
    name="releasy",
    version=__version__,
    author="Joran Beasley",
    author_email="joranbeasley@gmail.com",
    url="{url}",
    description="Help with versioning and release to pypi of projects",
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts':['rel-easy=releasy.cli:main','releasy=releasy.cli:main'],
    },

    # uncomment for auto install requirements
    # install_requires=['click','bs4','requests','six','pySystem'],
    # uncomment for classifiers
    classifiers=[
       "Programming Language :: Python :: 3",
       "License :: OSI Approved :: MIT License",
       "Operating System :: OS Independent",
    ],

    # uncomment for python version requirements
    python_requires='>=2.7',
)
##### END ###################################
