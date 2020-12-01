import configparser
import os
import re

# hacky backport that works in all python
isidentifier = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*$").match


class OSFindPackages:
    frontier = []
    seen = set()
    needle = None

    def __init__(self, cwd, ignore_patterns=('venv')):
        self.frontier = [os.path.abspath(cwd)]
        self.seen = set()
        self.needle = None

    def find_first(self, needle="__init__.py"):
        for result in self.find_all(needle):
            return result

    def find_all(self, needle="__init__.py"):
        self.needle = needle
        while len(self.frontier):
            next_item = self.frontier.pop(0)
            if next_item in self.seen:
                continue
            match = self.explore(next_item)
            if match:
                yield self.convert(match)

    def convert_to_package(self, dirname):
        return PkgData(dirname)

    def search_item(self, item):
        pkg_name = os.path.basename(item)
        files = os.listdir(item)
        for fname in files:
            if fname == self.needle and isidentifier(pkg_name):
                return item
            else:
                fpath = os.path.abspath(os.path.join(item, fname))
                if not os.path.isdir(fpath) or fpath in self.seen:
                    continue

    def explore(self, item):
        self.seen.add(item)
        self.search_item(item)


class PkgData:
    def __init__(self, pkg_path):
        pkg_path = os.path.abspath(pkg_path)
        assert os.path.isdir(pkg_path) and os.path.exists("__init__.py"), "Invalid PACKAGE DIR"
        self.pkg_path = pkg_path
        self.pkg_dir = os.path.dirname(pkg_path)
        self.pkg_name = os.path.basename(pkg_path)
        self.init_py = os.path.join(pkg_path, "__init__.py")
        self.ver_py = os.path.join(pkg_path, "version.py")
        self.setup_py = os.path.join(self.pkg_dir, "setup.py")
    # def version(self):
    #     if os.path.exists()


class PypiRc:
    """

    """

    def __init__(self):
        self.fpath = os.path.join(os.path.expanduser("~/.pypirc"))
        self.config = self.load()

    def index_urls(self):
        return list(filter(None, self.config['distutils']['index-servers'].splitlines()))

    def add_index_url(self, url):
        self.config['distutils']['index-servers'] += "\n{0}".format(url)

    def set_index_urls(self, *urls):
        self.config['distutils']['index-servers'] += "\n{0}".format([''] + urls)

    def save(self):
        self.config.write(open(self.fpath, "w"))

    def load(self):
        self.config = configparser.ConfigParser()
        self.config.read(self.fpath)
        if 'distutils' not in self.config.sections():
            self.config.add_section('distutils')
        if 'index-servers' not in self.config['distutils']:
            self.config['distutils']['index-servers'] = ''
        return self.config

    def create_or_update_alias_section(self, alias, repository=None, username=None, password=None):
        keys = 'repository', 'username', 'password'
        vals = [repository, username, password]
        data_dict = {k: v for k, v in zip(keys, vals) if v is not None}
        if alias not in self.config.sections():
            self.config.add_section(alias)
        print("Update Section:", data_dict)
        self.config[alias].update(data_dict)

    def get(self, alias, default=None):
        if alias in self.config.sections():
            return self.config[alias]
        return default

    def remove_alias(self, alias):
        self.config.remove_section(alias)
        index_urls = self.index_urls()
        index_urls.remove(alias)
        self.set_index_urls(*index_urls)

    def set_alias(self, alias, repository=None, username=None, password=None):
        self.create_or_update_alias_section(alias, repository, username, password)
        if alias not in self.index_urls():
            self.add_index_url(alias)
