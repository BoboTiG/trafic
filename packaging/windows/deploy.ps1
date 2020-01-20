# Usage: powershell ".\packaging\windows\deploy.ps1" [ARG]
#
# Possible ARG:
#     -build: build the installer
#     -check_upgrade: check the auto-update works
#     -install: install all dependencies
#     -install_release: install all but test dependencies
#     -start: start the application
#     -tests: launch the tests suite
#
# Source: https://github.com/nuxeo/nuxeo-drive/blob/master/tools/windows/deploy_jenkins_slave.ps1
#
# ---
#
# You can tweak tests checks by setting the SKIP envar:
#    - SKIP=flake8 to skip code style
#    - SKIP=mypy to skip type annotations
#    - SKIP=cleanup to skip dead code checks
#    - SKIP=rerun to not rerun failed test(s)
#    - SKIP=integration to not run integration tests on Windows
#    - SKIP=all to skip all above (equivalent to flake8,mypy,rerun,integration)
#    - SKIP=tests tu run only code checks
#
# There is no strict syntax about multiple skips (coma, coma + space, no separator, ... ).
#
param (
	[switch]$build = $false,
	[switch]$check_upgrade = $false,
	[switch]$install = $false,
	[switch]$install_release = $false,
	[switch]$start = $false,
	[switch]$tests = $false
)

# Stop the execution on the first error
$ErrorActionPreference = "Stop"

# Global variables
$global:PYTHON_OPT = "-Xutf8", "-E", "-s"
$global:PIP_OPT = "-m", "pip", "install", "--upgrade", "--upgrade-strategy=only-if-needed"


function add_missing_ddls {
	# Missing DLLS for Windows 7
	$folder = "C:\Program Files (x86)\Windows Kits\10\Redist\ucrt\DLLs\x86\"
	if (Test-Path $folder) {
		Get-ChildItem $folder | Copy -Verbose -Force -Destination "dist\$Env:APP_NAME_DIST"
	}
}

function build($app_real_version, $script) {
	# Build an executable
	Write-Output ">>> [$app_real_version] Building $script"
	if (-Not (Test-Path "$Env:ISCC_PATH")) {
		Write-Output ">>> ISCC does not exist: $Env:ISCC_PATH. Aborting."
		ExitWithCode 1
	}

	# Remove the beta notation
	$app_version = $app_real_version.split("b")[0]

	& $Env:ISCC_PATH\iscc /DMyAppVersion="$app_version" /DMyAppVersion="$app_version" /DMyAppRealVersion="$app_real_version" "$script"
	if ($lastExitCode -ne 0) {
		ExitWithCode $lastExitCode
	}
}

function build_installer {
	# Build the installer
	$app_version = (Get-Content $Env:APP_NAME_DIST\__init__.py) -match "__version__" -replace '"', "" -replace "__version__ = ", ""

	Write-Output ">>> [$app_version] Freezing the application"
	freeze_pyinstaller

	& $Env:STORAGE_DIR\Scripts\python.exe $global:PYTHON_OPT packaging\scripts\cleanup_application_tree.py "dist\$Env:APP_NAME_DIST"
	add_missing_ddls

	# Stop now if we only want the application to be frozen (for integration tests)
	if ($Env:FREEZE_ONLY) {
		return 0
	}

	build "$app_version" "packaging\windows\setup.iss"
}

function check_import($import) {
	# Check module import to know if it must be installed
	# i.e: check_import "from PyQt4 import QtWebKit"
	#  or: check_import "import cx_Freeze"
	& $Env:STORAGE_DIR\Scripts\python.exe $global:PYTHON_OPT -c $import
	if ($lastExitCode -eq 0) {
		return 1
	}
	return 0
}

function check_upgrade {
	# Ensure a new version can be released by checking the auto-update process.
    & $Env:STORAGE_DIR\Scripts\python.exe $global:PYTHON_OPT packaging\scripts\check_update_process.py
	if ($lastExitCode -ne 0) {
		ExitWithCode $lastExitCode
	}
}


function check_vars {
	# Check required variables
	if (-Not ($Env:PYTHON_VERSION)) {
		$Env:PYTHON_VERSION = '3.8.1'  # XXX_PYTHON
	} elseif (-Not ($Env:WORKSPACE)) {
		Write-Output ">>> WORKSPACE not defined. Aborting."
		ExitWithCode 1
	}
	if (-Not ($Env:ISCC_PATH)) {
		$Env:ISCC_PATH = "C:\Program Files (x86)\Inno Setup 6"  # XXX_INNO_SETUP
	}
	if (-Not ($Env:PYTHON_DIR)) {
		$ver_major, $ver_minor = $Env:PYTHON_VERSION.split('.')[0,1]
		$Env:PYTHON_DIR = "C:\Python$ver_major$ver_minor-32"
	}

	$Env:STORAGE_DIR = (New-Item -ItemType Directory -Force -Path "$($Env:WORKSPACE)\..\deploy-dir\$Env:PYTHON_VERSION").FullName

	Write-Output "    PYTHON_VERSION = $Env:PYTHON_VERSION"
	Write-Output "    WORKSPACE      = $Env:WORKSPACE"
	Write-Output "    STORAGE_DIR    = $Env:STORAGE_DIR"
	Write-Output "    PYTHON_DIR     = $Env:PYTHON_DIR"
	Write-Output "    ISCC_PATH      = $Env:ISCC_PATH"

	if (-Not ($Env:SPECIFIC_TEST) -Or ($Env:SPECIFIC_TEST -eq "")) {
		$Env:SPECIFIC_TEST = "$Env:REPOSITORY_NAME\tests"
	} else {
		Write-Output "    SPECIFIC_TEST  = $Env:SPECIFIC_TEST"
		$Env:SPECIFIC_TEST = "$Env:REPOSITORY_NAME\tests\$Env:SPECIFIC_TEST"
	}

	if (-Not ($Env:SKIP)) {
		$Env:SKIP = ""
	} else {
		Write-Output "    SKIP           = $Env:SKIP"
	}
}

function ExitWithCode($retCode) {
	$host.SetShouldExit($retCode)
	exit
}

function freeze_pyinstaller() {
	# Note: -OO option cannot be set with PyInstaller
	& $Env:STORAGE_DIR\Scripts\python.exe $global:PYTHON_OPT -m PyInstaller "$Env:REPOSITORY_NAME.spec" --noconfirm

	if ($lastExitCode -ne 0) {
		ExitWithCode $lastExitCode
	}
}

function install_deps {
	if (-Not (check_import "import pip")) {
		Write-Output ">>> Installing pip"
		# https://github.com/python/cpython/blob/master/Tools/msi/pip/pip.wxs#L28
		& $Env:STORAGE_DIR\Scripts\python.exe $global:PYTHON_OPT -OO -m ensurepip -U --default-pip
		if ($lastExitCode -ne 0) {
			ExitWithCode $lastExitCode
		}
	}

	Write-Output ">>> Installing requirements"
	& $Env:STORAGE_DIR\Scripts\python.exe $global:PYTHON_OPT -OO $global:PIP_OPT pip
	if ($lastExitCode -ne 0) {
		ExitWithCode $lastExitCode
	}
	& $Env:STORAGE_DIR\Scripts\python.exe $global:PYTHON_OPT -OO $global:PIP_OPT -r requirements.txt
	if ($lastExitCode -ne 0) {
		ExitWithCode $lastExitCode
	}
	& $Env:STORAGE_DIR\Scripts\python.exe $global:PYTHON_OPT -OO $global:PIP_OPT -r requirements-dev.txt
	if ($lastExitCode -ne 0) {
		ExitWithCode $lastExitCode
	}
}

function install_python {
	if (Test-Path "$Env:STORAGE_DIR\Scripts\activate.bat") {
		& $Env:STORAGE_DIR\Scripts\activate.bat
		if ($lastExitCode -ne 0) {
			ExitWithCode $lastExitCode
		}
		return
	}

	Write-Output ">>> Setting-up the Python virtual environment"

	& $Env:PYTHON_DIR\python.exe $global:PYTHON_OPT -OO -m venv --copies "$Env:STORAGE_DIR"
	if ($lastExitCode -ne 0) {
		ExitWithCode $lastExitCode
	}

	& $Env:STORAGE_DIR\Scripts\activate.bat
	if ($lastExitCode -ne 0) {
		ExitWithCode $lastExitCode
	}
}

function launch_test($path, $pytest_args) {
	# Launch tests on a specific path. On failure, retry failed tests.
	& $Env:STORAGE_DIR\Scripts\python.exe $global:PYTHON_OPT -bb -Wall -m pytest $pytest_args "$path"
	if ($lastExitCode -eq 0) {
		return
	}

	if (-not ($Env:SKIP -match 'rerun' -or $Env:SKIP -match 'all')) {
		# Do not fail on error as all failures will be re-run another time at the end
		& $Env:STORAGE_DIR\Scripts\python.exe $global:PYTHON_OPT -bb -Wall -m pytest `
			--last-failed --last-failed-no-failures none
	}
}

function launch_tests {
	# If a specific test is asked, just run it and bypass all over checks
	if ($Env:SPECIFIC_TEST -ne "tests") {
		Write-Output ">>> Launching the tests suite"
		launch_test "$Env:SPECIFIC_TEST"
		return
	}

	if (-not ($Env:SKIP -match 'flake8' -or $Env:SKIP -match 'all')) {
		Write-Output ">>> Checking the style"
		& $Env:STORAGE_DIR\Scripts\python.exe $global:PYTHON_OPT -m flake8 .
		if ($lastExitCode -ne 0) {
			ExitWithCode $lastExitCode
		}
	}

	if (-not ($Env:SKIP -match 'mypy' -or $Env:SKIP -match 'all')) {
		Write-Output ">>> Checking type annotations"
		& $Env:STORAGE_DIR\Scripts\python.exe $global:PYTHON_OPT -m mypy $Env:REPOSITORY_NAME
		if ($lastExitCode -ne 0) {
			ExitWithCode $lastExitCode
		}
	}

	if (-not ($Env:SKIP -match 'cleanup' -or $Env:SKIP -match 'all')) {
		Write-Output ">>> Checking for dead code"
		& $Env:STORAGE_DIR\Scripts\python.exe $global:PYTHON_OPT -m vulture $Env:REPOSITORY_NAME tools\whitelist.py
		if ($lastExitCode -ne 0) {
			ExitWithCode $lastExitCode
		}
	}

	if (-not ($Env:SKIP -match 'tests')) {
		Write-Output ">>> Launching tests"
		launch_test "watermark\tests"
	}

	# if (-not ($Env:SKIP -match 'integration' -or $Env:SKIP -match 'all')) {
	#	Write-Output ">>> Freezing the application for integration tests"
	#	$Env:FREEZE_ONLY = 1
	#	build_installer
	#
	#	Write-Output ">>> Launching integration tests"
	#	launch_test "$Env:REPOSITORY_NAME\tests\integration\windows" "-n0"
	# }
}

function start_app {
	# Start the application
	$Env:PYTHONPATH = "$Env:WORKSPACE"
	& $Env:STORAGE_DIR\Scripts\python.exe $global:PYTHON_OPT -OO -m $Env:REPOSITORY_NAME
}

function main {
	# Launch operations
	check_vars
	install_python

	if ($build) {
		build_installer
	} elseif ($check_upgrade) {
		check_upgrade
	} elseif ($install -or $install_release) {
		install_deps
		if ((check_import "import PyQt5") -ne 1) {
			Write-Output ">>> No PyQt5. Installation failed."
			ExitWithCode 1
		}
	} elseif ($start) {
		start_app
	} elseif ($tests) {
		launch_tests
	}
}

main
