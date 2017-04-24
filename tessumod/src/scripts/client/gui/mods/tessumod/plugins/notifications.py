# TessuMod: Mod for integrating TeamSpeak into World of Tanks
# Copyright (C) 2017  Janne Hakonen
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

from gui.mods.tessumod import plugintypes
from gui.mods.tessumod.lib import logutils, gameapi
from gui.mods.tessumod.lib.pluginmanager import Plugin

logger = logutils.logger.getChild("notifications")

class NotificationsPlugin(Plugin, plugintypes.Notifications):
	"""
	This plugin ...
	"""

	def __init__(self):
		super(NotificationsPlugin, self).__init__()

	@logutils.trace_call(logger)
	def initialize(self):
		pass

	@logutils.trace_call(logger)
	def deinitialize(self):
		pass

	@logutils.trace_call(logger)
	def show_notification(self, data):
		"""
		Implemented from Notifications.
		"""
		gameapi.show_notification(data)
