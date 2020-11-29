import importlib
import os
import re
import shutil
import subprocess
import sys

import click

from releasy import SemVersion
from releasy.util import find_package_paths, path_to_package_candidate


def click_promptChoice(*choices,default=None,prompt="Select One"):
    prompt = "  "+ "\n  ".join("%d. %s"%(i,c) for i,c in enumerate(choices,1))  +"\n%s"%prompt
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

@click.group()
@click.pass_context
def cli(ctx):
    pass
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
def rev(major,minor,build,extra,**kwds):
    package = kwds['package_dir']
    if not os.path.exists(os.path.join(package['package_dir'],package['package'],"version.py")):
        executable = click.get_current_context().command_path.split(" ",1)[0]
        raise RuntimeError("You MUST run `%s init` first"%executable)

    major = kwds.get('major2', major) or major
    minor = kwds.get('minor2', minor) or minor
    build = kwds.get('build2', build) or build
    extra = kwds.get('extra2', extra) or extra
    oldDir = os.getcwd()
    os.chdir(package['package_dir'])
    pkg = importlib.import_module(package['package']+".version","version")
    os.chdir(oldDir)

    otherVer = SemVersion.from_string(pkg.__version__)
    otherVer.extra_tag = extra
    otherVer.version_tuple = tuple(a+b for a,b in zip([major,minor,build],otherVer.version_tuple))
    otherVer.version = ".".join(map(str,otherVer.version_tuple))
    if kwds.get("git_hash"):
        hash = os.popen("git log --pretty=%H -1").read()
    create_version_file(package['package'], package['package_dir'], str(otherVer),hash="")
    print("SET VERSION: %s" % otherVer)

@cli.command()
@click.argument("which",type=click.Choice(["major","minor","build"],case_sensitive=False),default="build")
@click.option("-p","--package_dir",type=click_package,default=list(find_package_paths(".")))
@click.option("-g","--git-hash",is_flag=True,default=False)
def bump(**kwds):
    package = kwds['package_dir']
    if not os.path.exists(os.path.join(package['package_dir'], package['package'], "version.py")):
        executable = click.get_current_context().command_path.split(" ", 1)[0]
        raise RuntimeError("You MUST run `%s init` first" % executable)
    oldDir = os.getcwd()
    os.chdir(package['package_dir'])
    pkg = importlib.import_module(package['package'] + ".version", "version")
    os.chdir(oldDir)
    otherVer = SemVersion.from_string(pkg.__version__)
    if kwds['which'] == "major":
        otherVer.set(otherVer.major+1,0,0)
    if kwds['which'] == "minor":
        otherVer.set(otherVer.major,otherVer.minor+1,0)
    if kwds['which'] == "build":
        otherVer.set(otherVer.major,otherVer.minor,otherVer.build+1)
    create_version_file(package['package'], package['package_dir'], str(otherVer), hash="")
    print("SET VERSION: %s"%otherVer)

@cli.command("set")
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
@click.option("-g","--git-hash",is_flag=True,default=False)
def set_ver(major,minor,build,extra,**kwds):
    package = kwds['package_dir']
    if not os.path.exists(os.path.join(package['package_dir'], package['package'], "version.py")):
        executable = click.get_current_context().command_path.split(" ", 1)[0]
        raise RuntimeError("You MUST run `%s init` first" % executable)
    major = kwds.get('major2', major) or major
    minor = kwds.get('minor2', minor) or minor
    build = kwds.get('build2', build) or build
    extra = kwds.get('extra2', extra) or extra
    if kwds.get('version'):
        try:
            ver = SemVersion.from_string(kwds.get('version'))
        except:
            ver = SemVersion(major, minor, build, extra)
    else:
        ver = SemVersion(major, minor, build, extra)
    create_version_file(package['package'], package['package_dir'], str(ver), hash="")
    print("SET VERSION: %s"%ver)

def build_and_clean(package_dir):
    print(package_dir, sys.executable)
    files = set()
    if os.path.exists(os.path.join(package_dir['package_dir'],"dist")):
        files = set(os.listdir(os.path.join(package_dir['package_dir'],"dist")))
    p = subprocess.Popen([sys.executable, "./setup.py", "build", "sdist", "bdist_wheel"],
                         cwd=package_dir['package_dir'], stdout=sys.stdout)
    p.communicate()
    dirX = package_dir['package_dir']
    shutil.rmtree(os.path.join(dirX, "build"))
    shutil.rmtree(os.path.join(dirX, "versioning.egg-info"))
    shutil.rmtree(os.path.join(dirX, package_dir['package'], "__pycache__"))
    return list(set(os.listdir(os.path.join(package_dir['package_dir'], "dist"))).difference(files))

@cli.command("publish")
@click.option("-p","--package_dir",type=click_package,default=list(find_package_paths(".")))
@click.option("-u","--username",type=str,default=None)
@click.option("-p","--pasword",type=str,default=None)
@click.option("-t","--token",type=str,default=None)
@click.option("-r",type=str,default="pypi")
def deploy_pypi(package_dir,**kwds):
    if kwds.get('token'):
        kwds.update({'username':"__token__",'password':kwd['token']})
    import distutils.spawn
    from twine.cli import dispatch

    # twine = distutils.spawn.find_executable("twine")
    args = ["upload","--non-interactive","-r",kwds.get("repository")]
    new_files = build_and_clean(package_dir)
    if kwds.get("username"):
        args.extend(["-u",kwds["username"]])
    if kwds.get("password"):
        args.extend(["-p",kwds["password"]])
    # dispatch(args)

    # subprocess.Popen([twine])
    # print("NEW FILES",new_files)

@cli.command()
@click.argument("major",type=int,default=0,required=False)
@click.argument("minor",type=int,default=0,required=False)
@click.argument("build",type=int,default=0,required=False)
@click.argument("extra",type=str,default="",required=False)
@click.option("-M","--major","major2",type=int,default=None,required=False)
@click.option("-m","--minor","minor2",type=int,default=None,required=False)
@click.option("-b","--build","build2",type=int,default=None,required=False)
@click.option("-x","--extra","extra2",type=str,default=None,required=False)
@click.option("-v","--verString",type=str,default=None,required=False)
@click.option("-s","--setuppy",type=click.Choice(["y","n","prompt"],case_sensitive=False),default="prompt",required=False)
@click.option("-p","--package_dir",type=click_package,default=list(find_package_paths(".")))
@click.option("-g","--git-hash",is_flag=True,default=False)
@click.option("--gh-action","--add-github-deploy-action",type=click.Choice("yN",case_sensitive=False),default=None)
def init(major,minor,build,extra,**kwds):
    major = kwds.get('major2',major) or major
    minor = kwds.get('minor2',minor) or minor
    build = kwds.get('build2',build) or build
    extra = kwds.get('extra2',extra) or extra
    if kwds.get('verStr'):
        try:
            ver = SemVersion.from_string(kwds.get('verStr'))
        except:
            ver = SemVersion(major,minor,build,extra)
    else:
        ver = SemVersion(major,minor,build,extra)
    package = kwds['package_dir']
    # pkg0 = packages[0]
    if kwds.get("git_hash"):
        hash = os.popen("git log --pretty=%H -1").read()
        print("H:",hash)
    create_version_file(package['package'], package['package_dir'], str(ver),hash="")
    if not os.path.exists("{package_dir}/setup.py".format(**package)):
        r = click.prompt("Create setup.py?",default="y",type=click.Choice("yn",case_sensitive=False))
        if r.lower() == "y":
            d = {}
            d.update(**kwds)
            d.update(**package)
            create_setup_py(**d)
    else:
        setup_txt = open("{package_dir}/setup.py".format(**package)).read()
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

def create_version_file(package,package_dir,verString,sha_hash="",**kwds):
    ppath = os.path.join(package_dir,package)
    pi1 = open(os.path.join(ppath,"__init__.py"),"r").read()
    pi2 = re.sub("","",pi1)
    with open(os.path.join(ppath,"version.py"),"w") as f:
        if sha_hash and re.match("^[0-9a-fA-F]+$",sha_hash.strip()):
            sha_hash = "__hash__ = \"%s\""%sha_hash
        ver_tmpl_path = os.path.join(os.path.dirname(__file__),"DATA","version.tmpl")
        template = open(ver_tmpl_path,"r").read().format(VER=verString,HASH=sha_hash)
        f.write(template)
def create_setup_py(package,package_dir,**kwds):
    if kwds.get('package_name'):
        pkg_name = kwds.get('package_name')
    else:
        pkg_name = package
        if not kwds.get('yes'):
            pkg_name = click.prompt("--package-name", default=package)
    if kwds.get('description'):
        pkg_desc = kwds.get('description')
    else:
        pkg_desc = "This is just some project"
        if not kwds.get('yes'):
            pkg_desc = click.prompt("--description", default=pkg_desc)
    if kwds.get('author'):
        pkg_author = kwds.get('author')
    else:
        pkg_author = "anony mouse <anyone@email.com>"
        if not kwds.get('yes'):
            pkg_author = click.prompt("--author", default="anony mouse <anyone@email.com>")
    pkg_email = ""
    if kwds.get('email'):
        pkg_email = kwds.get('email')
    elif "@" in pkg_author:
        pkg = {'email': None}
        def matcher(m):
            name = " ".join(map(str.title, m.groups()[:2]))
            pkg['email'] = m.group(3)
            return name
        pkg_author = re.sub("([^ ]+)\s+([^ ]+)?\s*<?\s*([^\s]+@[^\s]+\.[^\s]+)\s*>\s*", matcher, pkg_author)
        pkg_email = pkg['email']
    if not pkg_email:
        pkg_email = "anony mouse <anyone@email.com>"
        if not kwds.get('yes'):
            pkg_email = click.prompt("--email", default="anony mouse <anyone@email.com>")
    pkg_site = kwds.get("site","{url}")


    # author = click.prompt("--package-author", default="anony mouse <anyone@email.com>")
    fmt_data = dict(
        VERSIONING=os.path.basename(os.path.abspath(os.path.dirname(__file__))),
        PKG=package,
        SITE=pkg_site,
        PKG_NAME=pkg_name,
        EMAIL=pkg_email,
        AUTHOR=pkg_author,
        DESCRIPTION=pkg_desc,
    )
    p = os.path.join(os.path.dirname(__file__),"DATA","setup_py.tmpl")
    s = open(p).read().format(**fmt_data)
    with open("{0}/setup.py".format(package_dir), "w") as f:
        f.write(s)


cli()
