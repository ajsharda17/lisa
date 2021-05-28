# Install LISA

- [Install LISA](#install-lisa)
  - [Prerequisites](#prerequisites)
  - [Install Python](#install-python)
    - [Install Python in Linux](#install-python-in-linux)
    - [Install Python in Windows](#install-python-in-windows)
  - [Install dependencies](#install-dependencies)
    - [Install dependencies in Linux](#install-dependencies-in-linux)
    - [Install dependencies in Windows](#install-dependencies-in-windows)
  - [Clone code](#clone-code)
  - [Install Poetry](#install-poetry)
    - [Install Poetry in Linux](#install-poetry-in-linux)
    - [Install Poetry in Windows](#install-poetry-in-windows)
  - [FAQ and Troubleshooting](#faq-and-troubleshooting)

LISA can be used to run test against the local node, or a remote node; if it is used to run 
against a remote node, you don't need to configure anything on the remote node.

![deploy](img/deploy.svg)

LISA can be launched on a Windows or a Linux OS. Follow below steps to install LISA
on your OS.


## Prerequisites

LISA needs to be installed on a computer which has network access the platform and the node to be tested. 

- It is recommended that this computer at least has 2 CPU cores and 4GB memory.


## Install Python

LISA has been tested on [Python 3.8 64 bits](https://www.python.org/). The latest version of
Python 3 is recommended. If you found LISA is not compatible with higher version Python,
[please file an issue](https://github.com/microsoft/lisa/issues/new).

#### Install Python in Linux

Refer below example to to install Python 3.8 in Ubuntu 20.04.

```bash
sudo apt update
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt install python3.8 python3.8-dev -y
```

#### Install Python in Windows

Navigate to [Python releases for
Windows](https://www.python.org/downloads/windows/). Download and install
*Windows installer (64-bit)* from Python 3.8 64-bits or higher version.


## Install dependencies

Please install `git` on your computer to clone LISA source code from this repo.

#### Install dependencies in Linux

In Linux, for exmaple, on Ubuntu 20.04, please use below command to install the dependencies:

```bash
sudo apt install git gcc libgirepository1.0-dev libcairo2-dev virtualenv -y
```

#### Install dependencies in Windows

In Windows, you need to install [git](https://git-scm.com/downloads), 
`virtualenv`(`pip install virtualenv`) and [Visual C++ 
redistributable package](https://aka.ms/vs/16/release/vc_redist.x64.exe)


## Clone code

```sh
git clone https://github.com/microsoft/lisa.git
cd lisa
```


## Install Poetry

Poetry is used to manage Python dependencies of LISA. Execute corresponding
script to install Poetry.

WARNING: Please enter LISA source code root folder to run below command to install poetry, 
since Poetry manages dependencies by the working folder.

#### Install Poetry in Linux

```bash
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | python3 -
source ../.profile
poetry install
```

#### Install Poetry in Windows

Launch `PowerShell` as Administrator, then execute below commands:

```powershell
(Invoke-WebRequest -Uri https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py -UseBasicParsing).Content | python -
# Add to PATH Poetry's binary location (either this or via Window's global env. vars. menu):
$env:PATH += ";$env:APPDATA\Python\Scripts"
poetry install
```


## FAQ and Troubleshooting

Refer to [FAQ and troubleshooting](troubleshooting.md).