# TessuMod: Mod for integrating TeamSpeak into World of Tanks
# Copyright (C) 2016  Janne Hakonen
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
# USA

Param([switch]$FromVagrant=$False)

$REPOPATH               = "C:\vagrant"
$WOTPATH                = "C:\world_of_tanks"
$LOCALCHOCOREPOPATH     = "$REPOPATH\chocolatey-repo"
$ALTERNATIVEPROFILEPATH = "$HOME\PowerShell_profile.ps1"
$PYTHONSCRIPTSPATH      = "C:\tools\python2\Scripts"
$MSVCPATH               = "C:\Program Files (x86)\Microsoft Visual Studio 12.0\VC"

$CHOCOLATEYURL          = "https://chocolatey.org/install.ps1"

function Add-EnvPath([string]$path) {
    $paths = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::Machine) -split ";"
    if ($paths -notcontains $path) {
        $paths = $paths + $path | where { $_ }
        [Environment]::SetEnvironmentVariable("Path", $paths -join ";", [EnvironmentVariableTarget]::Machine)
    }
}

function Set-PathExists([string]$path) {
    New-Item -ItemType Directory -Path $path -Force | Out-Null
}

# From http://stackoverflow.com/questions/3919798/how-to-check-if-a-cmdlet-exists-in-powershell-at-runtime-via-script#3919904
function Test-Command([string]$name) {
    [bool](Get-Command -Name $name -ErrorAction SilentlyContinue)
}

function Test-ChocoLocalPackageExists([string]$name) {
    [bool](choco list $name -r -e --pre -s local)
}

function Test-ChocoIsPackageInstalled([string]$name) {
    [bool](choco list $name -r -e --pre -l)
}

# A check to make sure we don't accitentally run this script against our host machine
if (-Not $FromVagrant) {
    Write-Host "This script is meant to be executed only on Vagrant provisioning phase, exiting..."
    Exit
}

$stopWatch = [Diagnostics.Stopwatch]::StartNew()

# Allow execution without any security prompts
Set-ExecutionPolicy -ExecutionPolicy Bypass -Force

# Since we are doing heavy activity in the file system, disabling Windows Defender's realtime
# monitoring speeds up whole bootstrapping
Set-MpPreference -DisableRealtimeMonitoring $true

# Disable automatic Windows updates, since Vagrant will not wait for update to gracefully finish
# if it takes too long to shutdown
Stop-Service wuauserv
Set-Service wuauserv -StartupType disabled

if (-Not (Test-Command "choco")) {
    Write-Host "Installing Chocolatey package manager"
    iex ((new-object net.webclient).DownloadString($CHOCOLATEYURL))
    # Hack for https://github.com/chocolatey/choco/issues/834
    mv $profile $ALTERNATIVEPROFILEPATH
}

. $ALTERNATIVEPROFILEPATH

# Enable installing locally packaged Chocolatey packages
Set-PathExists $LOCALCHOCOREPOPATH
choco source add --name=local --source=$LOCALCHOCOREPOPATH

Write-Host "Installing packages with Chocolatey..."
# See https://chocolatey.org/packages
choco install visualstudioexpress2013windowsdesktop --version 12.0.21005.1 -y
choco install jom --version 1.1.1 -y
choco install 7zip --version 16.02 -y
choco install python2 --version 2.7.11 -y
choco install git --version 2.9.2 -y
choco install cmake --version 3.6.0 -y

# Add programs to PATH
Add-EnvPath -path $PYTHONSCRIPTSPATH
Add-EnvPath "C:\Program Files\CMake\bin"
RefreshEnv

# Create Chocolatey package for Qt libraries
if (-Not (Test-ChocoLocalPackageExists qt-everywhere-opensource)) {
    powershell -NoProfile -Command "& $REPOPATH\chocolatey\qt-everywhere-opensource\tools\pack.ps1"
    if (Test-ChocoIsPackageInstalled qt-everywhere-opensource) {
        choco uninstall qt-everywhere-opensource
    }
}

# Install Qt libraries
choco install qt-everywhere-opensource --version 5.5.1 -y

# Create Chocolatey package for OpenAL Soft
if (-Not (Test-ChocoLocalPackageExists openal-soft)) {
    powershell -NoProfile -Command "& $REPOPATH\chocolatey\openal-soft\tools\pack.ps1"
    if (Test-ChocoIsPackageInstalled openal-soft) {
        choco uninstall openal-soft
    }
}

# Install OpenAL Soft
choco install openal-soft --version 1.16.0-fixes1 -y

RefreshEnv

cd $REPOPATH

Write-Host "Installing python dependencies..."
pip install -r requirements.txt

Write-Host "Configuring TessuMod development environment..."
python make.py configure --qmake-x86="$env:QT32PATH\bin\qmake.exe"
python make.py configure --qmake-x64="$env:QT64PATH\bin\qmake.exe"
python make.py configure --openal-x86=$env:OAL32PATH
python make.py configure --openal-x64=$env:OAL64PATH
python make.py configure --msvc-vars="$MSVCPATH\vcvarsall.bat"
python make.py configure --wot-install=$WOTPATH

$stopWatch.Stop()
Write-Host ("Bootstrapping took {0:N0} minutes" -f $stopWatch.Elapsed.TotalMinutes)
