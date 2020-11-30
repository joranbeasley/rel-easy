from .semversion import SemVersion
try:
    from .version import __version__
except:
    __version__="0.0.0"
