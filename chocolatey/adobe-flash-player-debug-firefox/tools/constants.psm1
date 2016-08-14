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

$ROOTPATH         = "$PSScriptRoot\.."
$REPOPATH         = "$ROOTPATH\..\..\chocolatey-repo"
$PACKAGENAME      = "adobe-flash-player-debug-firefox.22.0.nupkg"
$PACKAGEBUILDPATH = "$ROOTPATH\$PACKAGENAME"
$PACKAGEREPOPATH  = "$REPOPATH\$PACKAGENAME"
$INSTALLERPATH    = "$ROOTPATH\flashplayer_22_plugin_debug.exe"
$INSTALLERURL     = "https://fpdownload.macromedia.com/pub/flashplayer/updaters/22/flashplayer_22_plugin_debug.exe"

Export-ModuleMember -Variable *
