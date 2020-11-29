import os
import re
import shutil
import subprocess
import sys

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
def build_and_publish(package_dir,repository="pypi",username=None,password=None,token=None):
    new_files = build_and_clean(package_dir)
    push_to_pypi(new_files,repository=repository,username=username,password=password,token=token)
    return new_files

def push_to_pypi(new_files,token=None,username=None,password=None,repository="pypi"):
    from twine.cli import dispatch
    if token:
        username = "__token__"
        password = token

    args = ["upload","--non-interactive","-r",repository]

    if username:
        args.extend(["-u",username])
    if password:
        args.extend(["-p",password])
    args.extend(new_files)
    print("ARGS:",args)
    dispatch(args)
    return [os.path.basename(f) for f in new_files]

def build_and_clean(package_dir):
    print(package_dir, sys.executable)
    old_files = set()
    dist_dir = os.path.join(package_dir['package_dir'], "dist")
    if os.path.exists(dist_dir):
        old_files = set(map(lambda f:os.path.join(dist_dir,f),os.listdir(dist_dir)))
    p = subprocess.Popen([sys.executable, "./setup.py", "build", "sdist", "bdist_wheel"],
                         cwd=package_dir['package_dir'], stdout=sys.stdout)
    p.communicate()
    dirX = package_dir['package_dir']
    shutil.rmtree(os.path.join(dirX, "build"))
    shutil.rmtree(os.path.join(dirX, "%s.egg-info"%(package_dir['package'])))
    shutil.rmtree(os.path.join(dirX, package_dir['package'], "__pycache__"))
    new_files = set(map(lambda f:os.path.join(dist_dir,f),os.listdir(dist_dir)))
    return list(new_files.difference(old_files))


def create_version_file(package, package_dir, verString, sha_hash="", **kwds):
    ppath = os.path.join(package_dir, package)
    pi1 = open(os.path.join(ppath, "__init__.py"), "r").read()
    pi2 = re.sub("", "", pi1)
    with open(os.path.join(ppath, "version.py"), "w") as f:
        if sha_hash and re.match("^[0-9a-fA-F]+$", sha_hash.strip()):
            sha_hash = "__hash__ = \"%s\"" % sha_hash
        ver_tmpl_path = os.path.join(os.path.dirname(__file__), "DATA", "version.tmpl")
        template = open(ver_tmpl_path, "r").read().format(VER=verString, HASH=sha_hash)
        f.write(template)

def create_setup_py(fpath,pkg_name,pkg_desc,pkg_author,pkg_email,pkg_site):
    fmt_data = dict(
        VERSIONING=os.path.basename(os.path.abspath(os.path.dirname(__file__))),
        PKG=pkg_name,
        SITE=pkg_site,
        PKG_NAME=pkg_name,
        EMAIL=pkg_email,
        AUTHOR=pkg_author,
        DESCRIPTION=pkg_desc,
    )
    p = os.path.join(os.path.dirname(__file__), "DATA", "setup_py.tmpl")
    s = open(p).read().format(**fmt_data)
    with open(fpath, "w") as f:
        f.write(s)

def get_or_prompt(kwds,option,bypass_prompt,default,prompt_fn):
    key = option.strip("--").replace("-","_")
    if kwds.get(key):
        return kwds[key]
    if kwds.get(bypass_prompt):
        return default
    return prompt_fn(option,default=default)

def seperate_name_and_email(s):
    pkg = {'email': None}
    def matcher(m):
        name = " ".join(map(str.title, m.groups()[:2]))
        pkg['email'] = m.group(3)
        return name
    pkg['author'] = re.sub("([^ ]+)\s+([^ ]+)?\s*<?\s*([^\s]+@[^\s]+\.[^\s]+)\s*>\s*", matcher, s)
    return pkg

