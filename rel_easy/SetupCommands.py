import os


import distutils.cmd
import distutils.log
import distutils.spawn
import sys

import setuptools
import subprocess


class ReleaseCommand(distutils.cmd.Command):
    description = "build and push release to pypi (needs twine to be configured)"
    user_options = [
        ("repository=","r","the repository to use or an alias in ~/.pypirc"),
        ("username=","u","the twine username(if not setup in ~/.pypirc)"),
        ("password=","p","the twine password(if not setup in ~/.pypirc)"),
        ("yes","y","skip prompt when deploying to sources other than pypi"),
        ("version=","v","optional version string")
    ]

    def finalize_options(self):
        if self.repository != "testpypi":
            print("Are you sure you wish to deploy to %s LIVE?"%self.repository)
            result = sys.stdin.readline()
            if result and result[0].lower() != "y":
                print("FALL BACK to testPYPI")
                self.repository = "testpypi"
            else:
                print("Continue to deploy to %s"%self.repository)
        else:
            print("DEPLOY TO TESTPYPI ... to deploy to actual pypi, supply -r pypi")

        # if self.test:
        #     self.repository = 'testpypi'
        # else:
        #     print("Are you sure you wish to deploy to pypi LIVE?")
        #     result = sys.stdin.readline()
        #     if result and result[0].lower() == "y":
        #         self.repository = 'pypi'
        #     else:
        #         self.repository = 'testpypi'

    def initialize_options(self):
        """Set default values for options."""
        # Each user option must be listed here with their default value.
        self.repository = 'testpypi'
        self.username = None
        self.password = None
        self.version = None
        self.test = True

    def run(self):
        """Run command."""
        command = ['releasy',"publish","-r",self.repository]
        if self.username:
            command.append('--username=%s' % self.username)
            if not self.password:
                self.warn("You must provide both a username and a password")
                sys.exit(1)
            command.append('--password=%s' % self.password)
        if self.version:
            command.append("--version=%s"%self.version)
        # command.append(os.getcwd())
        distutils.spawn.spawn(command,verbose=True)
        self.announce(
            'Running command: %s' % str(command),
            level=distutils.log.INFO)
        print(subprocess.check_output(command))

class PylintCommand(distutils.cmd.Command):
  """A custom command to run Pylint on all Python source files."""

  description = 'run Pylint on Python source files'
  user_options = [
      # The format is (long option, short option, description).
      ('pylint-rcfile=', None, 'path to Pylint config file'),
  ]

  def initialize_options(self):
    """Set default values for options."""
    # Each user option must be listed here with their default value.
    self.pylint_rcfile = ''

  def finalize_options(self):
    """Post-process options."""
    if self.pylint_rcfile:
      assert os.path.exists(self.pylint_rcfile), (
          'Pylint config file %s does not exist.' % self.pylint_rcfile)

  def run(self):
    """Run command."""
    command = ['/usr/bin/pylint']
    if self.pylint_rcfile:
      command.append('--rcfile=%s' % self.pylint_rcfile)
    command.append(os.getcwd())
    self.announce(
        'Running command: %s' % str(command),
        level=distutils.log.INFO)
    subprocess.check_call(command)

if __name__ =="__main__":
    setuptools.setup(
        cmdclass={
            'pylint': PylintCommand,
            'release': ReleaseCommand,
        },
        # Usual setup() args.
        # ...
    )
