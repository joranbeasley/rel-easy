# rel-easy

making version management and pip package releases easy and FUN~

## Installation

install from pip

    pip install rel-easy
    
or install from source

    pip install https://github.com/joranbeasley/rel-easy.git
    
or clone and build from source

    git clone https://github.com/joranbeasley/rel-easy.git
    cd rel-easy
    python setup.py install

## Getting started
first install rel-easy (see install section above)

    pip install rel-easy

your directory structure should look as follows

   - `project_root`
      - `my_project`
         - `__init__.py`
         - `other.py`

run `rel-easy init` from the project root, it should automatically
   - identify `my_project` and prompt you to create a `setup.py`
   - if it cannot find a project it should prompt to create a new one
   - if it finds more than 1 package folder, it will prompt you for the main one
   
once initialized you can use various `rel-easy` \<commands\>
### Man Page

### Command Examples

#### Setting Version Directly
`rel-easy setver -v 2.1.0` would set the version to `2.1.0`

#### Bumping the version by one
`rel-easy bumpver` would change 2.1.3 to 2.1.4
`rel-easy bumpver build` would change 2.1.3 to 2.1.4
`rel-easy bumpver minor` would change 2.1.3 to 2.2.0
`rel-easy bumpver minor` would change 2.1.3 to 2.2.0

#### Releasing a new version to pypi or testpypi

PRE-REQUISITES
* **NOTE: you must first have created a pypi/testpypi account**
  * *this assumes you have a token generated we will refer to this as `<pypi_token>` and `<testpypi_token>` respectively*

##### BASIC RELEASE

`rel-easy release -r https://test.pypi.org/simple -u __token__ -p <testpypi_token>`

##### Only Build, No Upload (dry run)

you can do a dry run with `--build-only` flag, this skips the deploy step

there is no need to include a server or credentials with a dry run

`rel-easy --build-only`

##### SET Version and release

note: there is no way to `bumpver` or `rev` the version with the `release` subcommand, only setting a 
specific version
 
`rel-easy release -v 3.1.1 -r https://test.pypi.org/simple -u __token__ -p <testpypi_token>`

##### Alternative Authentication

- you can also edit your ~/.pypirc file to include other servers or put your credentials there
- you can set the ENVIRONMENT VARIABLES: `TWINE_PASSWORD` and `TWINE_USERNAME`
- when using the `github-deploy-action.yml` you MUST set the following `secrets`
  - for `pypi` or other servers set the secrets `PYPI_USERNAME` and `PIPI_PASSWORD`
  - for `testpypi` set the secrets `TESTPYPI_USERNAME` and `TESTPYPI_PASSWORD`
  - you can also use `PYPI_SERVER` to specify a distinct upload location

when using alternative authentication methods you do not have to include the username or password with the release command.

## Usage

to initialize rel-easy, simply run `rel-easy init` in the root of
your project, this will setup your package for release to pypi


## API Reference
