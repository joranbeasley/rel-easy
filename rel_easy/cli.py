import configparser
import importlib
import os
import re
import sys

import click

from rel_easy import SemVersion
from rel_easy.util import find_package_paths, path_to_package_candidate, create_setup_py, get_or_prompt, \
    seperate_name_and_email, build_and_clean, pypi_upload, create_version_file, temp_cwd, pypirc_parse_config, \
    pypirc_save_config_dict, pip_add_extra_index_url_to_conf, pip_get_conf_servers, pip_get_conf_path, \
    pip_delete_index_url_from_conf, pypirc_remove_section, pypirc_add_section_to_config


def click_promptChoice(*choices,**kwds):
    # print("K:",kwds)
    default = kwds.pop('default',None),
    if isinstance(default,(list,tuple)) and len(default)==1:
        default = default[0]
    # print("D:",default)
    prompt = kwds.pop('prompt',"Select One")
    prompt = "  "+ "\n  ".join("%d. %s"%(i,c) for i,c in enumerate(choices,1))  +"\n%s"%prompt
    # print("D:",default)
    result = click.prompt(prompt,type=int,default=default,show_default=default is not None)
    if result > len(choices):
        click.echo("ERROR: Invalid Choice %s. please select a number corresponding to your choice"%result)
        return click_promptChoice(*choices,default=default)
    return result-1,choices[result-1]

def click_package(s):
    if isinstance(s,(list,tuple)):
        packages = list(map(path_to_package_candidate,s))
        if len(packages) > 1:
            ix,package = click_promptChoice(*[p['package'] for p in packages])
            return packages[ix]
        elif len(packages) == 1:
            return packages[0]
        else:
            return None

    return path_to_package_candidate(s)
def print_version():
    from rel_easy import __version__
    print(__version__)
    exit(0)
@click.group()
@click.option("-v","--version",is_flag=True)
@click.pass_context
def cli(ctx,version=False):
    if not ctx.invoked_subcommand and version:
        print_version()


def require_init(fn):
    def __inner(*args,**kwargs):
        package = kwargs['package_dir']
        if not os.path.exists(os.path.join(package['package_dir'], package['package'], "version.py")):
            executable = click.get_current_context().command_path.split(" ", 1)[0]
            raise RuntimeError("You MUST run `%s init` first" % executable)
        fn(*args,**kwargs)
    return __inner

@cli.command()
@click.argument("major",type=int,default=0,required=False)
@click.argument("minor",type=int,default=0,required=False)
@click.argument("build",type=int,default=0,required=False)
@click.argument("extra",type=str,default="",required=False)
@click.option("-M","--major","major2",type=int,default=None,required=False)
@click.option("-m","--minor","minor2",type=int,default=None,required=False)
@click.option("-b","--build","build2",type=int,default=None,required=False)
@click.option("-x","--extra","extra2",type=str,default=None,required=False)
@click.option("-p","--package_dir",type=click_package,default=list(find_package_paths(".")))
@click.option("-g","--git-hash",is_flag=True,default=False)
@require_init
def rev(major,minor,build,extra,**kwds):
    package, package_dir = kwds['package_dir']['package'], kwds['package_dir']['package_dir']
    oldDir = os.getcwd()
    os.chdir(package_dir)
    pkg = importlib.import_module(package+".version","version")
    os.chdir(oldDir)
    otherVer = SemVersion.from_string(pkg.__version__)
    otherVer.extra_tag = extra
    otherVer.version_tuple = tuple(a+b for a,b in zip([major,minor,build],otherVer.version_tuple))
    otherVer.version = ".".join(map(str,otherVer.version_tuple))
    if kwds.get("git_hash"):
        hash = os.popen("git log --pretty=%H -1").read()
    create_version_file(package['package'], package['package_dir'], str(otherVer),hash="")
    print("SET VERSION: %s" % otherVer)

@cli.command(help="increase a version by one, resetting all lower versions to zero")
@click.argument("which",type=click.Choice(["major","minor","build"],case_sensitive=False),default="build")
@click.option("-p","--package_dir",type=click_package,default=list(find_package_paths(".")))
@click.option("-g","--git-hash",is_flag=True,default=False)
@require_init
def bumpver(**kwds):
    package,package_dir = kwds['package_dir']['package'], kwds['package_dir']['package_dir']
    pkg = _import_version(package,package_dir)
    otherVer = SemVersion.from_string(pkg.__version__)
    if kwds['which'] == "major":
        otherVer.set(otherVer.major+1,0,0)
    if kwds['which'] == "minor":
        otherVer.set(otherVer.major,otherVer.minor+1,0)
    if kwds['which'] == "build":
        otherVer.set(otherVer.major,otherVer.minor,otherVer.build+1)
    create_version_file(package, package_dir, str(otherVer), hash="")
    print("SET VERSION: %s"%otherVer)

@cli.command("setver")
@click.argument("major",type=int,default=0,required=False)
@click.argument("minor",type=int,default=0,required=False)
@click.argument("build",type=int,default=0,required=False)
@click.argument("extra",type=str,default="",required=False)
@click.option("-M","--major","major2",type=int,default=None,required=False)
@click.option("-m","--minor","minor2",type=int,default=None,required=False)
@click.option("-b","--build","build2",type=int,default=None,required=False)
@click.option("-x","--extra","extra2",type=str,default=None,required=False)
@click.option("-v","--version",type=str,default=None,required=False)
@click.option("-p","--package_dir",type=click_package,default=list(find_package_paths(".")))
@click.option("--sha1",is_flag=True,default=False)
def set_ver(major,minor,build,extra,sha1=False,**kwds):
    package = kwds['package_dir']
    # print("PKG:",package)
    if not os.path.exists(os.path.join(package['package_dir'], package['package'], "version.py")):
        executable = click.get_current_context().command_path.split(" ", 1)[0]
        raise RuntimeError("You MUST run `%s init` first" % executable)
    ver = None
    if kwds.get('version'):
        try:
            ver = SemVersion.from_string(kwds.get('version'))
        except:
            pass
    if not ver:
        major, minor, build, extra = _get_version_overrides(major,minor,build,extra,**kwds)
        ver = SemVersion(major, minor, build, extra)
    if sha1:
        git_hash = os.popen("git log --pretty=%H -1").read().strip()
    else:
        git_hash = ""
    create_version_file(package['package'], package['package_dir'], str(ver), sha_hash=git_hash)
    print("SET VERSION: %s"%ver)



@cli.command("publish",help="make build and push to pypi, does not bump version")
@click.option("-p","--package_dir",type=click_package,default=list(find_package_paths(".")))
@click.option("-u","--username",type=str,default=None)
@click.option("-p","--password",type=str,default=None)
@click.option("-t","--token",type=str,default=None)
@click.option("-r","--repository",type=str,default="pypi")
@click.option("-v","--version",default=None,type=SemVersion.from_string)
@click.option("--sha1",is_flag=True,default=False)
@click.option("-b","--build-only",is_flag=True,default=False)
def deploy_pypi(package_dir,version=None,sha1=False,build_only=False,**kwds):
    if version:
        if sha1:
            git_hash= os.popen("git log --pretty=%H -1").read().strip()
        else:
            git_hash=""
        create_version_file(package_dir['package'], package_dir['package_dir'], str(version), sha_hash=git_hash)
    new_files = build_and_clean(package_dir)
    click.echo("\n".join("Built: %s"%f for f in new_files))
    if not build_only:
        if not new_files:
            print("ERROR: No New Build, did you forget to update the version? or clear out old trial builds?")
            return []
        new_files = pypi_upload(new_files, **kwds)
        click.echo("\n".join("Built And Published: %s" % os.path.basename(f) for f in new_files))



@cli.command("init")
@click.argument("major",type=int,default=0,required=False)
@click.argument("minor",type=int,default=0,required=False)
@click.argument("build",type=int,default=0,required=False)
@click.argument("extra",type=str,default="",required=False)
@click.option("-M","--major","major2",type=int,default=None,required=False)
@click.option("-m","--minor","minor2",type=int,default=None,required=False)
@click.option("-b","--build","build2",type=int,default=None,required=False)
@click.option("-x","--extra","extra2",type=str,default=None,required=False)
@click.option("-v","--version",type=str,default=None,required=False)
@click.option("-s","--setuppy",type=click.Choice(["y","n","prompt"],case_sensitive=False),default="prompt",required=False)
@click.option("-p","--package_dir",type=click_package,default=list(find_package_paths(".")))
@click.option("--sha1",is_flag=True,default=False)
@click.option("--gh-action","--add-github-deploy-action",prompt=True,type=click.Choice("yN",case_sensitive=False),default=None)
def init(major,minor,build,extra,**kwds):
    package, package_dir = kwds['package_dir']['package'], kwds['package_dir']['package_dir']
    try:
        ver = SemVersion.from_string(kwds.get('version'))
    except:
        major, minor, build, extra = _get_version_overrides(major, minor, build, extra, **kwds)
        ver = SemVersion(major, minor, build, extra)
    sha_hash = ""
    if kwds.get("sha1"):
        sha_hash = os.popen("git log --pretty=%H -1").read()

    create_version_file(package, package_dir, str(ver),sha_hash=sha_hash)
    setup_path = os.path.join(package_dir,"setup.py")
    if not os.path.exists(setup_path):
        r = click.prompt("Create setup.py?",default="y",type=click.Choice("yn",case_sensitive=False))
        if r.lower() == "y":
            d = {}
            d.update(**kwds)
            d.update(**package)
            create_setup_py(setup_path, **_initialize_setup_py_kwds(d))
    else:
        setup_txt = open(setup_path).read()
        import_stmt = "from {package}.version import __version__".format(**package)
        if import_stmt not in setup_txt:
            r = click.prompt("It looks like we should update setup.py to use the version?", default="y", type=click.Choice("Yn", case_sensitive=False))
            if r.lower() == "y":
                setup_txt = "from {package}.version import __version__\n\n".format(**package) + setup_txt
                setup_txt = re.sub("version\s*=\s*.*","version=__version__,",setup_txt)
                with open("{package_dir}/setup.py".format(**package),"w") as f:
                    f.write(setup_txt)
        else:
            click.echo("setup.py is already configured")
    if kwds.get("gh_action")=="y":
        print( "INSTALLING .github/workflows/deploy.yml")
        dpath = "{package_dir}/.github/workflows/deploy.yml".format(**package)
        info = {'PKG':package['package'],'EXE':'versioner'}
        templ_path = os.path.join(os.path.dirname(__file__),"DATA","github-deploy-action-yml.tmpl")
        github_action_def = open(templ_path).read().format(**info)
        os.makedirs(os.path.dirname(dpath),exist_ok=True)
        with open(dpath, "w") as f:
            f.write(github_action_def)
        os.system("git add {package_dir}/.github/workflows/deploy.yml".format(**package))
        print("installed .github/workflows/deploy.yml")
def _import_version(package,package_dir):
    with temp_cwd(package_dir):
        pkg = importlib.import_module(package + ".version", "version")
def _get_version_overrides(major,minor,build,extra,**kwds):
    major = kwds.get('major2', major) or major
    minor = kwds.get('minor2', minor) or minor
    build = kwds.get('build2', build) or build
    extra = kwds.get('extra2', extra) or extra
    return major,minor,build,extra
def _initialize_setup_py_kwds(kwds):
    data = dict(
    pkg_name = get_or_prompt(kwds, '--package-name', 'yes', kwds['package'].replace("_", "-"), click.prompt),
    pkg_desc = get_or_prompt(kwds, '--description', "yes", "This is just some project", click.prompt),
    pkg_author = get_or_prompt(kwds, '--author', "yes", "anony mouse <anyone@email.com>", click.prompt)
    )
    pkg = seperate_name_and_email(data['pkg_author'])
    data['pkg_author'] = pkg['author']
    data['pkg_email'] = pkg.get('email', None) or kwds.get('email', None)
    if not data['pkg_email']:
        data['pkg_email'] = "anony mouse <anyone@email.com>"
        if not kwds.get('yes'):
            data['pkg_email'] = click.prompt("--email", default=data['pkg_email'])
    return data


@cli.group("pip-config",invoke_without_command=True)
@click.pass_context
def cli2(ctx):
    # print("G2",ctx)
    if not ctx.invoked_subcommand:
        print_install_servers()
        result = click_promptChoice("Add a New Server","Delete A Server","quit")[1]
        if result == "quit":
            print("OK QUIT")
            exit(0)
        if result == "Add a New Server":
            print("ADDD??")
            sys.argv.remove('pip-config')
            add_server()
        elif result == "Delete A Server":
            print("DELETE???")
            sys.argv.remove('pip-config')
            del_server()
@cli2.command("add-server")#"config-install-servers",help="add an install server for pip to pull from")
@click.option("--url",type=str,default=None,prompt=True)
@click.option("-y","--yes",is_flag=True)
def add_server(url=None,yes=False):
    add_install_server(url,yes)
def add_install_server(url,yes=False):
    if not yes:
        if not click.confirm("Are you sure you want to add: %s"%url):
            print("OK not adding server")
            exit(0)
    pip_add_extra_index_url_to_conf(url)

@cli2.command("del-server")#"config-install-servers",help="add an install server for pip to pull from")
@click.option("--url",type=str,default=None)
@click.option("-y","--yes",is_flag=True,default=False)
def del_server(url=None,yes=False):
    del_install_server(url,yes)
def del_install_server(url=None,yes=False):
    print("DEL:",url)
    if not url:
        servers = pip_get_conf_servers()
        urls = pip_get_conf_servers('extra-index-url', 'index-url')
        urls = list(filter(None,urls.get('extra-index-url',[])+urls.get('index-url',[])))
        if not urls:
            print("There are no custom urls to delete ... try adding some")
        result = click_promptChoice("Cancel Do Not Delete", *urls)[1]
        if result == "Cancel Do Not Delete":
            print("OK not deleting ANY server")
            exit(0)
        url = result
        data = pip_delete_index_url_from_conf(url)
    print("Delete Server:",url)



@cli2.command("list-servers")#"config-install-servers",help="add an install server for pip to pull from")
# @click.argument("url",type=str)
def list_servers():
    return print_install_servers()

def print_install_servers():
    from pip._internal.models.index import PyPI
    urls = pip_get_conf_servers('extra-index-url','index-url')
    # print("U:",urls)
    urls['index-url'] = ["[LOCKED] "+PyPI.simple_url] if len(urls.get('index-url',[])) < 2 else urls['index-url'][1:]
    urls['extra-index-url'] = ["<No Extra URLS>"] if len(urls['extra-index-url']) < 2 else urls['extra-index-url'][1:]
    click.echo("conf: %s"%(pip_get_conf_path(),))
    click.echo("index-url:\n - "+"\n - ".join(urls['index-url']))
    click.echo("extra-index-url:\n - "+"\n - ".join(urls['extra-index-url']))



@cli.group("config-deploy",invoke_without_command=True)
@click.pass_context
def cli3(ctx):
    # print("G2",ctx)
    if not ctx.invoked_subcommand:
        pypi_wizard()

def pypi_wizard():
    data = pypirc_parse_config()
    servers = print_servers("  [ N. NEW ]  [ D. DEL ]  [ X. EXIT ]")
    choices = ['n','d','x']
    choices.extend(map(str,range(1,len(servers)+1)))
    result = click.prompt("Choose an item to Edit or N,D,X",show_choices=False,
                          type=click.Choice(choices,case_sensitive=False))
    editing = False
    alias2 = None
    if result.isdigit():
        alias2 = {
            'name':servers[int(result)-1],
        }
        editing = alias2['name'] is not None
        alias2['data'] =  data.get(alias2['name'], {})
        result = "n"
    if result[0] == "n":
        if alias2 is None:
            alias = click.prompt("enter alias name for server")
        else:
            alias = alias2['name']
            click.echo("EDITING: %s"%alias)
        d = {'r':{},'u':{},'p':{}}
        if editing:
            d = {'r':{'default': alias2['data'].get('repository','')},
                     'u':{'default': alias2['data'].get('username','')},
                     'p':{'default': alias2['data'].get('password','')},
                 }
        repository = None
        if alias not in {'pypi','testpypi'}:
            repository = click.prompt("enter repository url for server", **d['r'])
        alias_data = dict(
                username= click.prompt("repository username",**d['u']),
                password= click.prompt("repository password",**d['p'])
            )
        if repository:
            alias_data['repository'] = repository
        if not editing:
            data['distutils']['index-servers'].append(alias)
        data.setdefault(alias,{}).update({k:v for k,v in alias_data.items() if v})
        msg = "Are you sure you wish to add this repository?"
        if editing:
            msg = msg[:25]+"finalize editing of server:%s ?"%(alias)
        if click.confirm(msg):
            pypirc_save_config_dict(data)
            if not editing and alias not in ['pypi','testpypi']:
                if click.confirm("Would you like to add a corresponding extra-index-url for pip install?"):
                    joiner = "://%s:%s@"%(alias_data['username'],alias_data['token'])
                    uri = joiner.join(alias_data['repository'].split("://"))
                    pip_add_extra_index_url_to_conf(uri)
    elif result[0] == "d":
        servers = print_servers("SELECT ITEM TO DELETE (or 'x' to exit)",show_counts=True)
        choices = ['x']
        choices.extend(map(str,range(1,len(servers)+1)))
        result = click.prompt("Choose an item to DELETE", show_choices=False,
                                  type=click.Choice(choices, case_sensitive=False))
        alias = servers[int(result)-1]


        if alias in {"pypi","testpypi"}:
            click.echo("You CANNOT DELETE %s"%alias)
            exit(0)
        if click.confirm("Are you sure you wish to delete %s "%alias):
            pypirc_remove_section(None,alias)
            print("Removed:",alias)
    elif result[0] == "x":
        click.echo("GoodBye")
        exit(0)

@cli3.command("del-server",help="setup and configure your deploy credentials and servers for pypi")
@click.option("-a","--alias",prompt=True)
def delete_pypirc_alias(alias):
    print("DELETE ALIAS",alias)

@cli3.command("add-server",help="setup and configure your deploy credentials and servers for pypi")
@click.option("-a","--alias",prompt=True)
@click.option("-r","--repository",prompt=True)
@click.option("-u","--username",prompt=True)
@click.option("-p","--password",prompt=True)
def add_pypirc_alias(alias,**kwds):
    pypirc_add_section_to_config(**kwds)
    print_servers()

def print_servers(prompt="",show_counts=False):
    data = pypirc_parse_config()
    servers = data.get('distutils', {'index-servers': ['']})['index-servers'][1:]
    sz = 20
    ct_fmt = ""
    if show_counts:
        sz = 17
        ct_fmt="{0: 2d}."

    if len(servers):
        click.echo("Servers To Push Python Packages To")
        if prompt:
            click.echo(prompt)
        click.echo("  alias          | url")
        click.echo("  ---------------+----------------------")
        for i,server in enumerate(servers):
            d = data.get(server, {})
            url = d.get('repository', "*INTERNAL  CREDS ONLY*")
            if len(url) > 49:
                url = "...".join([url[:18], url[-30:]])
            if d.get("username"):
                url = "//******@".join(url.split("//", 1))
            click.echo("  {ct_fmt}{0:<{1}s}| {2}".format(server, sz, url,ct_fmt=ct_fmt.format(i)))
    else:
        click.echo("No Servers found ... ")
    return servers

@cli3.command("list-servers",help="list pypi servers configured for uploading")
def list_pypirc_aliases():
    print_servers()
def configure_pypirc():
    pip_add_extra_index_url_to_conf("adsa")
    while True:
        data = pypirc_parse_config()
        servers = data.get('distutils',{'index-servers':['']})['index-servers'][1:]
        servers_options = servers[:]
        servers_options.insert(0,"Delete a Server")
        servers_options.insert(0,"Add a new Server")
        servers_options.append("Quit")
        result = click_promptChoice(*servers_options,default=1)[1]
        alias = None
        editing = None
        print("R:",result)
        if result == "QUIT":
            sys.exit(0)
        if result in servers:
            print("EDIT EXISTING!!")
            alias = result
            editing = alias
            result = "Add a new Server"
        if result == "Delete a Server":
            server = click_promptChoice(*["Cancel Deletion",]+servers,default=1)
            print("DELETE SERVER:",server)
        elif result == "Add a new Server":
            if alias is None:
                alias = click.prompt("enter alias name for server")
            d = {}
            if editing:
                d = {'r':{'default': data[editing].get('repository','')},
                     'u':{'default': data[editing].get('username','')},
                     'p':{'default': data[editing].get('password','')},
                     }
            print(":D:",d)
            alias_data = dict(
                repository = click.prompt("enter repository url for server",**d['r']),
                username= click.prompt("repository username",**d['u']),
                password= click.prompt("repository password",**d['p'])
            )
            if not editing:
                data['distutils']['index-servers'].append(alias)
            data.setdefault(alias,{}).update({k:v for k,v in alias_data.items() if v})
            if click.confirm("Are you sure you wish to add this repository?"):
                pypirc_save_config_dict(data)
                if not editing and alias not in ['pypi','testpypi']:
                    if click.confirm("Would you like to add a corresponding extra-index-url for pip?"):
                        joiner = "://%s:%s@"%(alias_data['username'],alias_data['token'])
                        uri = joiner.join(alias_data['repository'].split("://"))
                        pip_add_extra_index_url_to_conf(uri)

cli()
