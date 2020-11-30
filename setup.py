##### Created By releasy ##########################
import setuptools
from rel_easy.version import __version__
from rel_easy.SetupCommands import ReleaseCommand
setuptools.setup(
    name="rel-easy",
    version=__version__,
    author="Joran Beasley",
    author_email="joranbeasley@gmail.com",
    url="https://github.com/joranbeasley/rel-easy",
    description="Help with versioning and release to pypi of projects",
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts':['rel-easy=rel_easy.cli:main',
                           'releasy=rel_easy.cli:main'],
    },
    package_data={
        # If any package contains *.txt files, include them:
        "rel_easy": ["DATA/*.tmpl"]}
    ,
    # uncomment for auto install requirements
    install_requires=['click','six'],
    # uncomment for classifiers
    classifiers=[
       "Programming Language :: Python :: 3",
       "License :: OSI Approved :: MIT License",
       "Operating System :: OS Independent",
    ],
    cmdclass={
        'release': ReleaseCommand,
    },
    # uncomment for python version requirements
    python_requires='>=2.7',
)
##### END ###################################
