import os

from future.utils import isidentifier

def path_to_package_candidate(path):
    pdir = os.path.dirname(path)
    pname = os.path.basename(path)
    return {"package_dir": pdir, 'package': pname}

def find_package_paths(cwd,ignore_patterns=("venv",)):
    """
    # >>> print(os.getcwd())
    >>> for r in find_package_candidates(".."):
    ...     print(r)

    :param cwd:
    :return:
    """
    dir_frontier = [os.path.abspath(cwd)]
    seen = set()
    while dir_frontier:
        curdir = dir_frontier.pop(0)
        pname = os.path.basename(curdir)
        pdir = os.path.dirname(curdir)
        if isidentifier(pname):
            files = os.listdir(curdir)
            for fname in files:
                if fname == "__init__.py":
                    yield curdir
                else:
                    fpath = os.path.join(curdir, fname)
                    if fname[0] not in "_." and os.path.isdir(fpath):
                        if not any(pat in fname for pat in ignore_patterns):
                            # print("APPEND:",fname)
                            dir_frontier.append(fpath)



        # print("C:",pname,isidentifier(pname),"F:",files)
