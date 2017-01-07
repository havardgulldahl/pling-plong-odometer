#!/bin/bash

# setup-pyqt-mac.sh -- set up a complete pyqt4 system on mac

DOWNLOADS_SDIR=downloads
WORKING_SDIR=working


function require_success {
    local status=$?
    local message=$1
    if [ "$status" != "0" ]; then
        echo $message
        exit $status
    fi
}

function patch_sys_python {
    # Fixes error discussed here:
    # http://stackoverflow.com/questions/22313407/clang-error-unknown-argument-mno-fused-madd-python-package-installation-fa
    # Present for OSX 10.9.2 fixed in 10.9.3
    # This should be benign for 10.9.3 though
    local py_sys_dir="/System/Library/Frameworks/Python.framework/Versions/2.7/lib/python2.7"
    pushd $py_sys_dir
    if [ -n "`grep fused-madd _sysconfigdata.py`" ]; then
        sudo sed -i '.old' 's/ -m\(no-\)\{0,1\}fused-madd//g' _sysconfigdata.py
        sudo rm _sysconfigdata.pyo _sysconfigdata.pyc
    fi
    popd
}


function system_install_pip {
    # Install pip into system python
    sudo easy_install pip
    PIP_CMD="sudo /usr/local/bin/pip"
}

function install_pythonorg {
    PY_URL="https://www.python.org/ftp/python/2.7.3/python-2.7.3-macosx10.6.dmg"

}

function install_pyqt {
    # download pyqtx and install it
    PYQTX_URL="http://downloads.sourceforge.net/project/pyqtx/Complete/PyQtX%2B_py273_q482_pyqt494.pkg.mpkg.zip?r=https%3A%2F%2Fsourceforge.net%2Fprojects%2Fpyqtx%2Ffiles%2FComplete%2F&ts=1483815319&use_mirror=netcologne"
    INSTALLER="$DOWNLOADS_SDIR/pyqtx_installer.mpkg"
    curl "$PYQTX_URL" -o "$INSTALLER.zip"
    require_success "Couldnt download pyqtx from sourceforge"
    unzip "$INSTALLER.zip"
    require_success "Couldnt unzip pyqtx installer"
    sudo installer -pkg "$INSTALLER" -target /
    require_success "Installing pyqtx failed"



}


function system_install_virtualenv {
    # Install virtualenv into system python
    # Needs $PIP_CMD
    check_pip
    $PIP_CMD install virtualenv
    require_success "Failed to install virtualenv"
    VIRTUALENV_CMD="/usr/local/bin/virtualenv"
}


function remove_travis_ve_pip {
    # Remove travis installs of virtualenv and pip
    if [ "$(sudo which virtualenv)" == /usr/local/bin/virtualenv ]; then
        sudo pip uninstall -y virtualenv;
    fi
    if [ "$(sudo which pip)" == /usr/local/bin/pip ]; then
        sudo pip uninstall -y pip;
    fi
}



####
# MAIN

#PYTHON_EXE="/usr/bin/python"
#remove_travis_ve_pip
install_pyqt
#system_install_pip




####

# install pyqt 

