# Deployment Script

We are using scripts to automate the isolated environment creation. With only one script, you will be able to setup the environment and build the Drive package.

## GNU/Linux, macOS

### Usage

```shell
sh installer/$OSI/deploy.sh [ARG]
```

Where `$OSI` is one of: `linux`, `osx`.

Possible `ARG`:

    --build: freeze the application into self-hosted binary package
    --install: install all dependencies
    --start: start the application

### Dependencies:

See [pyenv](https://github.com/yyuu/pyenv/wiki/Common-build-problems#requirements) requirements.

## Windows

**PowerShell 4.0 or above** is required to run this script. You can find installation instructions [here](https://docs.microsoft.com/en-us/powershell/scripting/setup/installing-windows-powershell).

### Usage

```batch
powershell .\installer\windows\deploy.ps1 [ARG]
```

Possible `ARG`:

    -build: freeze the application into self-hosted binary package
    -install: install all dependencies
    -start: start the application

### Dependencies:

- [Python 3.6.7](https://www.python.org/ftp/python/3.6.7/python-3.6.7.exe) or newer.
- [Inno Setup 5.5.9 (u)](http://www.jrsoftware.org/download.php/is-unicode.exe) to create the installer.

### Troubleshooting

If you get an error message complaining about the lack of signature for this script, you can disable that security check with the following command inside PowerShell (as Administrator):

```batch
set-executionpolicy -executionpolicy unrestricted
```

## Environment Variables

### Required Envars

- `WORKSPACE` is the **absolute path to the WORKSPACE**, i.e. `/opt/jenkins/workspace/xxx`.
- `WORKSPACE_SRC` is the **absolute path to application sources**, i.e. `$WORKSPACE/sources`. If not defined, it will be set to `$WORKSPACE/sources` or `$WORKSPACE/trafic` if folder exists else `$WORKSPACE`.

### Optional Envars

- `PYTHON_VERSION` is the required **Python version** to use, i.e. `3.6.7`.
- `SIGNING_ID` is the certificate **authority name**.

#### MacOS Specific

Those are related to code-signing:
- `KEYCHAIN_PATH` is the **full path** to the certificate.
- `KEYCHAIN_PWD` is the **password** to unlock the certificate.

#### Windows Specific

- `APP_NAME` is the **application name** used for code sign, i.e. `Trafic`.
- `APP_NAME_LOWER` is the **application name** in lower case (used internally), i.e. `trafic`.
- `ISCC_PATH` is the **Inno Setup path** to use, i.e. `C:\Program Files (x86)\Inno Setup 5`.
- `PYTHON_DIR` is the **Python path** to use, i.e. `C:\Python36-32`.
- `SIGNTOOL_PATH` is the **SignTool path** to use, i.e. `C:\Program Files (x86)\Windows Kits\10\App Certification Kit`.
