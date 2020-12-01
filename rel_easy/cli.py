import importlib
import os
import re
import sys
from functools import wraps

import click

from rel_easy import SemVersion
from rel_easy.consts import VER_NAMES, ERR_NO_NEW_FILES
from rel_easy.releasy_pkg_data import PypiRc
from rel_easy.util import find_package_paths, path_to_package_candidate, create_setup_py, \
    get_or_prompt, separate_name_and_email, build_and_clean, pypi_upload, create_version_file, \
    temp_cwd, pypirc_parse_config,  pip_add_extra_index_url_to_conf, \
    pip_get_conf_servers, pip_get_conf_path, pip_delete_index_url_from_conf, \
    pypirc_add_section_to_config


def click_promptChoice(*choices, **kwds):
    # print("K:",kwds)
    default = kwds.pop('default', None),
    if isinstance(default, (list, tuple)) and len(default) == 1:
        default = default[0]
    # print("D:",default)
    prompt = kwds.pop('prompt', "Select One")
    index_strings = ("%d. %s" % (i, c) for i, c in enumerate(choices, 1))
    prompt = "  " + "\n  ".join(index_strings) + "\n%s" % prompt
    # print("D:",default)
    result = click.prompt(prompt, type=int, default=default, show_default=default is not None)
    if result > len(choices):
        err_msg = "ERROR: Invalid Choice %s. please select a number corresponding to your choice"
        click.echo(err_msg % result)
        return click_promptChoice(*choices, default=default)
    return result - 1, choices[result - 1]


def click_package(s):
    if isinstance(s, (list, tuple)):
        packages = list(map(path_to_package_candidate, s))
        if len(packages) > 1:
            ix, package = click_promptChoice(*[p['package'] for p in packages])
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
@click.option("-v", "--version", is_flag=True)
@click.pass_context
def cli(ctx, version=False):
    if not ctx.invoked_subcommand and version:
        print_version()


def require_init(fn):
    @wraps(fn)
    def __inner(*args, **kwargs):
        package = kwargs['package_dir']
        pkg_name, pkg_dir = package['package_dir'], package['package']
        if not os.path.exists(os.path.join(pkg_name, pkg_dir, "version.py")):
            executable = click.get_current_context().command_path.split(" ", 1)[0]
            raise RuntimeError("You MUST run `%s init` first" % executable)
        fn(*args, **kwargs)

    return __inner


@cli.command()
@click.argument("major", type=int, default=0, required=False)
@click.argument("minor", type=int, default=0, required=False)
@click.argument("build", type=int, default=0, required=False)
@click.argument("extra", type=str, default="", required=False)
@click.option("-M", "--major", "major2", type=int, default=None, required=False)
@click.option("-m", "--minor", "minor2", type=int, default=None, required=False)
@click.option("-b", "--build", "build2", type=int, default=None, required=False)
@click.option("-x", "--extra", "extra2", type=str, default=None, required=False)
@click.option("-p", "--package_dir", type=click_package, default=list(find_package_paths(".")))
@click.option("-g", "--git-hash", is_flag=True, default=False)
@require_init
def rev(major, minor, build, extra, **kwds):
    package, package_dir = kwds['package_dir']['package'], kwds['package_dir']['package_dir']
    old_dir = os.getcwd()
    os.chdir(package_dir)
    pkg = importlib.import_module(package + ".version", "version")
    os.chdir(old_dir)
    other_ver = SemVersion.from_string(pkg.__version__)
    other_ver.extra_tag = extra
    other_ver.version_tuple = tuple(a + b for a, b in zip([major, minor, build],
                                                          other_ver.version_tuple))
    other_ver.version = ".".join(map(str, other_ver.version_tuple))
    if kwds.get("git_hash"):
        sha_hash = os.popen("git log --pretty=%H -1").read()
    create_version_file(package['package'], package['package_dir'],
                        str(other_ver), sha_hash=sha_hash)
    print("SET VERSION: %s" % other_ver)


@cli.command(help="increase a version by one, "
                  "resetting all lower versions to zero")
@click.argument("which",
                type=click.Choice(VER_NAMES, case_sensitive=False),
                default="build")
@click.option("-p", "--package_dir", type=click_package,
              default=list(find_package_paths(".")))
@click.option("-g", "--git-hash", is_flag=True, default=False)
@require_init
def bumpver(**kwds):
    package, package_dir = kwds['package_dir']['package'], kwds['package_dir']['package_dir']
    pkg = _import_version(package, package_dir)
    otherVer = SemVersion.from_string(pkg.__version__)
    if kwds['which'] == "major":
        otherVer.set(otherVer.major + 1, 0, 0)
    if kwds['which'] == "minor":
        otherVer.set(otherVer.major, otherVer.minor + 1, 0)
    if kwds['which'] == "build":
        otherVer.set(otherVer.major, otherVer.minor, otherVer.build + 1)
    create_version_file(package, package_dir, str(otherVer), hash="")
    print("SET VERSION: %s" % otherVer)


@cli.command("setver")
@click.argument("major", type=int, default=0, required=False)
@click.argument("minor", type=int, default=0, required=False)
@click.argument("build", type=int, default=0, required=False)
@click.argument("extra", type=str, default="", required=False)
@click.option("-M", "--major", "major2", type=int, default=None, required=False)
@click.option("-m", "--minor", "minor2", type=int, default=None, required=False)
@click.option("-b", "--build", "build2", type=int, default=None, required=False)
@click.option("-x", "--extra", "extra2", type=str, default=None, required=False)
@click.option("-v", "--version", type=str, default=None, required=False)
@click.option("-p", "--package_dir", type=click_package, default=list(find_package_paths(".")))
@click.option("--sha1", is_flag=True, default=False)
def set_ver(major, minor, build, extra, sha1=False, **kwds):
    package = kwds['package_dir']
    # print("PKG:",package)
    if not os.path.exists(os.path.join(package['package_dir'], package['package'], "version.py")):
        executable = click.get_current_context().command_path.split(" ", 1)[0]
        raise RuntimeError("You MUST run `%s init` first" % executable)
    ver = None
    if kwds.get('version'):
        try:
            ver = SemVersion.from_string(kwds.get('version'))
        except TypeError:
            pass
    if not ver:
        major, minor, build, extra = _get_version_overrides(major, minor, build, extra, **kwds)
        ver = SemVersion(major, minor, build, extra)
    if sha1:
        git_hash = os.popen("git log --pretty=%H -1").read().strip()
    else:
        git_hash = ""
    create_version_file(package['package'], package['package_dir'], str(ver), sha_hash=git_hash)
    print("SET VERSION: %s" % ver)


@cli.command("publish", help="make build and push to pypi, does not bump version")
@click.option("-p", "--package_dir", type=click_package, default=list(find_package_paths(".")))
@click.option("-u", "--username", type=str, default=None)
@click.option("-p", "--password", type=str, default=None)
@click.option("-t", "--token", type=str, default=None)
@click.option("-r", "--repository", type=str, default="pypi")
@click.option("-v", "--version", default=None, type=SemVersion.from_string)
@click.option("--sha1", is_flag=True, default=False)
@click.option("-b", "--build-only", is_flag=True, default=False)
def deploy_pypi(package_dir, version=None, sha1=False, build_only=False, **kwds):
    pkg_name, pkg_dir = package_dir['package'], package_dir['package_dir']
    if version:
        if sha1:
            git_hash = os.popen("git log --pretty=%H -1").read().strip()
        else:
            git_hash = ""
        create_version_file(pkg_name, pkg_dir, str(version), sha_hash=git_hash)
    new_files = build_and_clean(package_dir)
    click.echo("\n".join("Built: %s" % f for f in new_files))
    if not build_only:
        if not new_files:
            print(ERR_NO_NEW_FILES)
            return []
        new_files = pypi_upload(new_files, **kwds)
        new_file_basenames = map(os.path.basename, new_files)
        click.echo("\n".join(map("Built And Published: {0}".format, new_file_basenames)))


@cli.command("init")
@click.argument("major", type=int, default=0, required=False)
@click.argument("minor", type=int, default=0, required=False)
@click.argument("build", type=int, default=0, required=False)
@click.argument("extra", type=str, default="", required=False)
@click.option("-M", "--major", "major2", type=int, default=None, required=False)
@click.option("-m", "--minor", "minor2", type=int, default=None, required=False)
@click.option("-b", "--build", "build2", type=int, default=None, required=False)
@click.option("-x", "--extra", "extra2", type=str, default=None, required=False)
@click.option("-v", "--version", type=str, default=None, required=False)
@click.option("-s", "--setuppy", default="prompt", required=False,
              type=click.Choice(["y", "n", "prompt"], case_sensitive=False))
@click.option("-p", "--package_dir", type=click_package, default=list(find_package_paths(".")))
@click.option("--sha1", is_flag=True, default=False)
@click.option("--gh-action", "--add-github-deploy-action", prompt=True,
              type=click.Choice("yN", case_sensitive=False), default=None)
def init(major, minor, build, extra, **kwds):
    do_create_version_file_and_get_version(major, minor, build, extra, **kwds)
    package = kwds['package_dir']
    package, package_dir = package['package'], package['package_dir']
    setup_path = os.path.join(package_dir, "setup.py")
    if not os.path.exists(setup_path):
        r = click.prompt("Create setup.py?", default="y",
                         type=click.Choice("yn", case_sensitive=False))
        if r.lower() == "y":
            d = {}
            d.update(**kwds)
            d.update(**package)
            create_setup_py(setup_path, **_initialize_setup_py_kwds(d))
    else:
        setup_txt = open(setup_path).read()
        import_stmt = "from {package}.version import __version__".format(**package)
        if import_stmt not in setup_txt:
            r = click.prompt("It looks like we should update setup.py to use the version?",
                             default="y", type=click.Choice("Yn", case_sensitive=False))
            if r.lower() == "y":
                import_text = "from {package}.version import __version__\n\n".format(**package)
                regex = r"version\s*=\s*.*", "version=__version__,"
                setup_txt = re.sub(regex, import_text + setup_txt)
                with open("{package_dir}/setup.py".format(**package), "w") as f:
                    f.write(setup_txt)
        else:
            click.echo("setup.py is already configured")
    if kwds.get("gh_action") == "y":
        click.echo("INSTALLING .github/workflows/deploy.yml")
        dpath = "{package_dir}/.github/workflows/deploy.yml".format(**package)
        info = {'PKG': package['package'], 'EXE': 'versioner'}
        templ_path = os.path.join(os.path.dirname(__file__),
                                  "DATA", "github-deploy-action-yml.tmpl")
        github_action_def = open(templ_path).read().format(**info)
        os.makedirs(os.path.dirname(dpath), exist_ok=True)
        with open(dpath, "w") as f:
            f.write(github_action_def)
        os.system("git add {package_dir}/.github/workflows/deploy.yml".format(**package))
        print("installed .github/workflows/deploy.yml")


def do_create_version_file_and_get_version(major, minor, build, extra, **kwds):
    package, package_dir = kwds['package_dir']['package'], kwds['package_dir']['package_dir']
    try:
        ver = SemVersion.from_string(kwds.get('version'))
    except TypeError:  # not the right type or not passed in
        major, minor, build, extra = _get_version_overrides(major, minor, build, extra, **kwds)
        ver = SemVersion(major, minor, build, extra)
    sha_hash = ""
    if kwds.get("sha1"):
        sha_hash = os.popen("git log --pretty=%H -1").read()

    create_version_file(package, package_dir, str(ver), sha_hash=sha_hash)
    return ver


def _import_version(package, package_dir):
    with temp_cwd(package_dir):
        pkg = importlib.import_module(package + ".version", "version")
    return pkg


def _get_version_overrides(major, minor, build, extra, **kwds):
    major = kwds.get('major2', major) or major
    minor = kwds.get('minor2', minor) or minor
    build = kwds.get('build2', build) or build
    extra = kwds.get('extra2', extra) or extra
    return major, minor, build, extra


def _initialize_setup_py_kwds(kwds):
    data = dict(
        pkg_name=get_or_prompt(kwds, '--package-name', 'yes',
                               kwds['package'].replace("_", "-"), click.prompt),
        pkg_desc=get_or_prompt(kwds, '--description', "yes",
                               "This is just some project", click.prompt),
        pkg_author=get_or_prompt(kwds, '--author', "yes",
                                 "anony mouse <anyone@email.com>", click.prompt)
    )
    pkg = separate_name_and_email(data['pkg_author'])
    data['pkg_author'] = pkg['author']
    data['pkg_email'] = pkg.get('email', None) or kwds.get('email', None)
    if not data['pkg_email']:
        data['pkg_email'] = "anony mouse <anyone@email.com>"
        if not kwds.get('yes'):
            data['pkg_email'] = click.prompt("--email", default=data['pkg_email'])
    return data


@cli.group("pip-config", invoke_without_command=True)
@click.pass_context
def cli2(ctx):
    # print("G2",ctx)
    if not ctx.invoked_subcommand:
        print_install_servers()
        result = click_promptChoice("Add a New Server", "Delete A Server", "quit")[1]
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


@cli2.command("add-server")
@click.option("--url", type=str, default=None, prompt=True)
@click.option("-y", "--yes", is_flag=True)
def add_server(url=None, yes=False):
    add_install_server(url, yes)


def add_install_server(url, yes=False):
    if not yes:
        if not click.confirm("Are you sure you want to add: %s" % url):
            print("OK not adding server")
            exit(0)
    pip_add_extra_index_url_to_conf(url)


@cli2.command("del-server")
@click.option("--url", type=str, default=None)
@click.option("-y", "--yes", is_flag=True, default=False)
def del_server(url=None, yes=False):
    del_install_server(url, yes)


def del_install_server(url=None, yes=False):
    print("DEL:", url)
    if not url:
        urls = pip_get_conf_servers('extra-index-url', 'index-url')
        urls = list(filter(None, urls.get('extra-index-url', []) + urls.get('index-url', [])))
        if not urls:
            print("There are no custom urls to delete ... try adding some")
        result = click_promptChoice("Cancel Do Not Delete", *urls)[1]
        if result == "Cancel Do Not Delete":
            print("OK not deleting ANY server")
            exit(0)
        url = result
        pip_delete_index_url_from_conf(url)
    print("Delete Server:", url)


@cli2.command("list-servers")
def list_servers():
    return print_install_servers()


def print_install_servers():
    from pip._internal.models.index import PyPI
    urls = pip_get_conf_servers('extra-index-url', 'index-url')
    # print("U:",urls)
    if len(urls.get('index-url', [])) < 2:
        urls['index-url'] = ["[LOCKED] " + PyPI.simple_url]
    else:
        urls['index-url'] = urls['index-url'][1:]
    if len(urls['extra-index-url']) < 2:
        urls['extra-index-url'] = ["<No Extra URLS>"]
    else:
        urls['index-url'] = urls['extra-index-url'][1:]
    click.echo("conf: %s" % (pip_get_conf_path(),))
    click.echo("index-url:\n - " + "\n - ".join(urls['index-url']))
    click.echo("extra-index-url:\n - " + "\n - ".join(urls['extra-index-url']))


@cli.group("config-deploy", invoke_without_command=True)
@click.pass_context
def cli3(ctx):
    # print("G2",ctx)
    if not ctx.invoked_subcommand:
        pypi_wizard()


def pypy_get_alias_choice_prompt(prompt1, prompt2):
    servers = print_pypirc_servers(prompt1, show_counts=True)
    choices = ['x']
    choices.extend(map(str, range(1, len(servers) + 1)))
    result = click.prompt(prompt2, show_choices=False,
                          type=click.Choice(choices, case_sensitive=False))
    return servers[int(result) - 1]


def pypi_wizard_root_prompt():
    servers = print_pypirc_servers("  [ N. NEW ]  [ D. DEL ]  [ X. EXIT ]")
    choices = ['n', 'd', 'x']
    choices.extend(map("{0}".format, range(1, len(servers) + 1)))
    result = click.prompt("Choose an item to Edit or N,D,X", show_choices=False,
                          type=click.Choice(choices, case_sensitive=False))
    action = {"action": "quit"}
    if result == "x":
        return
    if result.isdigit():
        action = {"action": "edit", "target": servers[int(result) - 1]}
    elif result == "n":
        action = {"action": "create"}
    elif result == "d":
        result = pypy_get_alias_choice_prompt("SELECT ITEM TO DELETE (or 'x' to exit)",
                                              "Choose an item to DELETE")
        action = {"action": "delete", "target": result}
    return action


def pypi_edit_or_create_prompt(alias=None, repository=None, username=None, password=None):
    KNOWN_ALIASES = {"pypi", "testpypi"}
    if alias:
        message = "EDIT PYPI DEPLOY TARGET: %s" % alias
    else:
        message = "Create New PYPI DEPLOY TARGET"
    click.echo(message)
    if alias not in KNOWN_ALIASES:
        repository = click.prompt("%s REPOSITORY URL:" % alias, default=repository)
    username = click.prompt("%s USERNAME:" % alias, default=repository)
    password = click.prompt("%s PASSWORD:" % alias, default=repository)
    return {'alias': alias, 'repository': repository, 'username': username, 'password': password}


def pypi_wizard():
    result = pypi_wizard_root_prompt()
    pypi_inst = PypiRc()
    if result['action'] == "quit":
        click.echo("GoodBye")
    elif result['action'] == "delete":
        click.echo("DELETE: %s" % (result['target']))
        pypi_inst.remove_alias(result['target'])
        pypi_inst.save()
    elif result['action'] in {"create", "edit"}:
        kwargs = dict(pypi_inst.get(result.get('target', "<NA>"), {}).items())
        result = pypi_edit_or_create_prompt(result.get('target', None), **kwargs)
        pypi_inst.set_alias(**result)
        pypi_inst.save()


@cli3.command("del-server", help="setup and configure your deploy credentials and servers for pypi")
@click.option("-a", "--alias", prompt=True)
def delete_pypirc_alias(alias):
    print("DELETE ALIAS", alias)


@cli3.command("add-server", help="setup and configure your deploy credentials and servers for pypi")
@click.option("-a", "--alias", prompt=True)
@click.option("-r", "--repository", prompt=True)
@click.option("-u", "--username", prompt=True)
@click.option("-p", "--password", prompt=True)
def add_pypirc_alias(alias, **kwds):
    pypirc_add_section_to_config(**kwds)
    print_pypirc_servers()


def print_pypirc_servers(prompt="", show_counts=False):
    data = pypirc_parse_config()
    servers = data.get('distutils', {'index-servers': ['']})['index-servers'][1:]
    sz = 20
    ct_fmt = ""
    if show_counts:
        sz = 17
        ct_fmt = "{0: 2d}."

    if len(servers):
        click.echo("Servers To Push Python Packages To")
        if prompt:
            click.echo(prompt)
        click.echo("  alias          | url")
        click.echo("  ---------------+----------------------")
        for i, server in enumerate(servers):
            d = data.get(server, {})
            url = d.get('repository', "*INTERNAL  CREDS ONLY*")
            if len(url) > 49:
                url = "...".join([url[:18], url[-30:]])
            if d.get("username"):
                url = "//******@".join(url.split("//", 1))
            click.echo("  {ct_fmt}{0:<{1}s}| {2}".format(server, sz, url, ct_fmt=ct_fmt.format(i)))
    else:
        click.echo("No Servers found ... ")
    return servers


@cli3.command("list-servers", help="list pypi servers configured for uploading")
def list_pypirc_aliases():
    print_pypirc_servers()


if __name__ == "__main__":
    cli()
