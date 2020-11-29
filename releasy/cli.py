import importlib
import os
import re
import shutil
import subprocess
import sys

import click

from releasy import SemVersion
from releasy.util import find_package_paths, path_to_package_candidate, create_setup_py, get_or_prompt, \
    seperate_name_and_email, build_and_clean, build_and_publish, push_to_pypi, create_version_file


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

@cli.command(help="increase a version by one, resetting all lower versions to zero")
@click.argument("which",type=click.Choice(["major","minor","build"],case_sensitive=False),default="build")
@click.option("-p","--package_dir",type=click_package,default=list(find_package_paths(".")))
@click.option("-g","--git-hash",is_flag=True,default=False)
def bumpver(**kwds):
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



@cli.command("publish",help="make build and push to pypi, does not bump version")
@click.option("-p","--package_dir",type=click_package,default=list(find_package_paths(".")))
@click.option("-u","--username",type=str,default=None)
@click.option("-p","--password",type=str,default=None)
@click.option("-t","--token",type=str,default=None)
@click.option("-r","--repository",type=str,default="pypi")
@click.option("-v","--versionstring",type=None)
@click.option("--sha1",is_flag=True,default=False)
@click.option("-b","--build-only",is_flag=True,default=False)
def deploy_pypi(package_dir,versionstring=None,sha1=False,build_only=False,**kwds):
    if versionstring:
        if sha1:
            git_hash= os.popen("git log --pretty=%H -1").read().strip()
        else:
            git_hash=""
        create_version_file(package_dir['package'], package_dir['package_dir'], str(versionstring), sha_hash=git_hash)
    new_files = build_and_clean(package_dir)
    click.echo("\n".join("Built: %s"%f for f in new_files))
    if not build_only:
        if not new_files:
            print("ERROR: No New Build, did you forget to update the version? or clear out old trial builds?")
            return []
        new_files = push_to_pypi(new_files,**kwds)
        click.echo("\n".join("Built And Published: %s" % os.path.basename(f) for f in new_files))



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
@click.option("--gh-action","--add-github-deploy-action",prompt=True,type=click.Choice("yN",case_sensitive=False),default=None)
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
            pkg_name = get_or_prompt(kwds, '--package-name', 'yes', package, click.prompt)
            pkg_desc = get_or_prompt(kwds, '--description', "yes", "This is just some project", click.prompt)
            pkg_author = get_or_prompt(kwds, '--author', "yes", "anony mouse <anyone@email.com>", click.prompt)
            pkg = seperate_name_and_email(pkg_author)
            pkg_author = pkg['author']
            pkg_email = pkg.get('email', None) or kwds.get('email', None)
            if not pkg_email:
                pkg_email = "anony mouse <anyone@email.com>"
                if not kwds.get('yes'):
                    pkg_email = click.prompt("--email", default=pkg_email)

            create_setup_py(pkg_name,pkg_desc,pkg_author,pkg_email,kwds.get('site',None))
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



cli()
