#!/bin/bash

# setup-python-mac.sh -- set up system python on mac

# inspired by terryfy

GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py
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

PYTHON_EXE="/usr/bin/python"
remove_travis_ve_pip
system_install_pip




####

# install mac apps

pip install py2app
