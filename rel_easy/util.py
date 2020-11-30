import configparser
import os
import platform
import re
import shutil
import subprocess
import sys
from contextlib import contextmanager

#hacky backport that works in all python
isidentifier = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*$").match
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
        # print("SEARCH:", curdir)
        if curdir in seen:
            continue
        seen.add(curdir)
        pname = os.path.basename(curdir)
        pdir = os.path.dirname(curdir)

        files = os.listdir(curdir)
        # print(" CheckFILES:",files)
        for fname in files:
            if fname.startswith("."):
                continue
            if fname == "__init__.py":
                if isidentifier(pname):
                    yield curdir
            else:
                fpath = os.path.join(curdir, fname)
                if fname[0] not in "_." and os.path.isdir(fpath):
                    if not any(pat in fname for pat in ignore_patterns):
                        # print("APPEND:",fname)
                        if fpath not in seen:
                            dir_frontier.append(fpath)




        # print("C:",pname,isidentifier(pname),"F:",files)
def build_and_publish(package_dir,repository="pypi",username=None,password=None,token=None):
    new_files = build_and_clean(package_dir)
    pypi_upload(new_files, repository=repository, username=username, password=password, token=token)
    return new_files

def pypirc_overwrite_config(sections, sectionDefs):
    config = configparser.ConfigParser()
    def addSection(cfg,sectionName,sectionDef):
        cfg.add_section(sectionName)
        for key in ['repository','username','password']:
            if sectionDef.get(key, None):
                config[s][key] = sectionDef[key]
    config.add_section("distutils")
    config["distutils"]["index-servers"]="\n"+"\n".join(sections)
    for s in sections:
        addSection(config,s,sectionDefs[s])
    config.write(sys.stdout)

def pypirc_parse_config():
    cfg = configparser.ConfigParser()
    cfg.read(os.path.expanduser("~/.pypirc"))
    data = {"distutils":{'index-servers':[''],}}
    for s in cfg.sections():
        if s == "distutils":
            if 'index-servers' in cfg[s]:
                ix = cfg[s]['index-servers'].splitlines()
                data[s] = {'index-servers':ix}
        else:
            data[s] = dict(cfg[s].items())
    return data
def pip_get_conf_path():
    fpath = "~/.config/pip/pip.conf"
    if platform.system() == "Windows":
        fpath = "~/AppData/Roaming/pip/pip.ini"
    return os.path.abspath(os.path.expanduser(fpath))
def pip_parse_conf():
    cfg = configparser.ConfigParser()
    fpath = pip_get_conf_path()
    fdir = os.path.basename(fpath)
    os.makedirs(fdir,exist_ok=True)
    cfg.read(fpath)
    data = {}
    for s in cfg.sections():
        for key,val in cfg[s].items():
            if "\n" in val:
                val = val.splitlines()
            data.setdefault(s,{})[key] = val
    return data
def pip_get_pip_global_urls():
    data = pip_parse_conf()
    print("D:",data)
def pip_get_conf_servers(*keys):
    data = pip_parse_conf()
    servers = {}

    for k in keys:
        servers2 = data.get('global', {}).get(k, None)
        if not isinstance(servers2,list):
            if servers2:
                servers2 = [servers2]
            else:
                continue
        assert isinstance(servers2,list)
        servers[k] = ['']+servers2 if not len(servers2) and servers2[0] != '' else servers2
    return servers

def pip_delete_index_url_from_conf(url):
    data = pip_parse_conf()
    if url in data.get('global',{}).get('index-url',[]):
        print("FOUND URL IN index-url")
        ix_list = data['global']['index-url']
        ix_list.remove(url)
        pip_save_config_dict(ix_list)
    elif url in data.get('global',{}).get('extra-index-url',[]):
        # print("FOUND URL IN extra-index-url")
        ix_list = data['global']['extra-index-url']
        ix_list.remove(url)
        pip_save_config_dict(data)
    else:
        raise ValueError("unable to find url %s in index-urls:\nLooked In %s"%(url,pip_get_conf_path()))

def pip_add_extra_index_url_to_conf(url):
    data = pip_parse_conf()
    data.setdefault('global',{}).setdefault('extra-index-url',None)
    if not isinstance(data['global']['extra-index-url'],list):
        data['global']['extra-index-url'] = ['',data['global']['extra-index-url']] if data['global']['extra-index-url'] else ['']
    if url not in data['global']['extra-index-url']:
        data['global']['extra-index-url'].append(url)
        pip_save_config_dict(data)
    else:
        print("CANNOT ADD '%s' ... its already there"%url)

def pip_save_config_dict(data,fpath=pip_get_conf_path()):
    pip_save_config(dict_with_arrays_to_config(data), fpath)
    print("SAVED CONFIG FILE:",fpath)

def pip_save_config(cfg, fpath=pip_get_conf_path()):
    if isinstance(cfg,dict):
        return pip_save_config_dict(cfg,fpath)
    if not isinstance(cfg,configparser.ConfigParser):
        raise TypeError("Expected a dict or ConfigParser got %r"%cfg)
    cfg.write(open(fpath,"w"))
    # print("SAVED CONFIG FILE!!")

def fix_dict_with_arrays_to_joined_strings(a_dict):
    data = {}
    for section in list(a_dict.keys()):
        data[section] = {}
        for key,value in list(a_dict[section].items()):
            if isinstance(value,(list,tuple)):
                data[section][key] = "\n".join(value)
            else:
                data[section][key] = value
    return data

def dict_with_arrays_to_config(d):
    cfg = configparser.ConfigParser()
    data = fix_dict_with_arrays_to_joined_strings(d)
    cfg.read_dict(data)
    return cfg

def pypirc_save_config(cfg, fpath=os.path.expanduser("~/.pypirc")):
    if isinstance(cfg,dict):
        return pypirc_save_config_dict(cfg)
    assert isinstance(cfg,configparser.ConfigParser)
    cfg.write(open(fpath,"w"))

def pypirc_save_config_dict(d, fpath=os.path.expanduser("~/.pypirc")):
    cfg = dict_with_arrays_to_config(d)
    pypirc_save_config(cfg, fpath)
# d = parse_pypirc()
# d['distutils']['index-servers'] = '\n'.join(d['distutils']['index-servers'])
# c = configparser.ConfigParser()
# c.read_dict(d)
def pypirc_remove_section(cfg, sectionName):
    if cfg is None:
        cfg = configparser.ConfigParser()
        cfg.read(os.path.expanduser("~/.pypirc"))
    if sectionName not in cfg:
        raise TypeError("Unable to get section: %s"%sectionName)
    ix_urls = cfg['distutils'].get('index-servers', "").splitlines()
    cfg.remove_section(sectionName)
    if sectionName in ix_urls:
        ix_urls.remove(sectionName)
        cfg['distutils']['index-servers'] = "\n".join(ix_urls)
    pypirc_save_config(cfg)

def pypirc_add_section_to_config(cfg, sectionName, **sectionDef):
    if cfg is None:
        cfg = configparser.ConfigParser()
        cfg.read(os.path.expanduser("~/.pypirc"))
    if sectionName not in cfg:
        ix_urls = cfg['distutils'].get('index-servers',"").splitlines()
        ix_urls.append(sectionName)
        cfg['distutils']['index-servers'] = "\n".join(ix_urls)
        cfg.add_section(sectionName)
    else:
        print("Section exists configure: %s"%sectionName)
    cfg[sectionName].update(sectionDef)
    cfg.write(sys.stdout)
    return cfg


# add_section_to_pypirc(None,"bob",**{"username":"__token__","repository":"http://asdasd.com/simple","password":"asdasdasdasdasdasd"})

def pypi_upload(new_files, token=None, username=None, password=None, repository="pypi"):
    from twine.cli import dispatch
    if token:
        username = "__token__"
        password = token

    args = ["upload","-r",repository]

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
    shutil.rmtree(os.path.join(dirX, "build"),ignore_errors=True)
    shutil.rmtree(os.path.join(dirX, "%s.egg-info"%(package_dir['package'])),ignore_errors=True)
    shutil.rmtree(os.path.join(dirX, package_dir['package'], "__pycache__"),ignore_errors=True)
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

@contextmanager
def temp_cwd(cwd):
    oldDir = os.getcwd()
    os.chdir(cwd)
    yield
    os.chdir(oldDir)

def create_setup_py(fpath,pkg_name,pkg_desc,pkg_author,pkg_email,pkg_site):
    fmt_data = dict(
        VERSIONING=os.path.basename(os.path.abspath(os.path.dirname(__file__))),
        PKG=pkg_name,
        SITE=pkg_site,
        PKG_NAME=pkg_name,
        PKG_NAME_DASHED=pkg_name.replace("_","-"),
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

