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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

class Plugin(object):

	CATEGORY = "Plugin"

	def __init__(self):
		super(Plugin, self).__init__()

	def initialize(self):
		pass

	def deinitialize(self):
		pass

	@property
	def messages(self):
		return self.__messages

	@messages.setter
	def messages(self, messages):
		self.__messages = messages

	@property
	def plugin_manager(self):
		return self.__plugin_manager

	@plugin_manager.setter
	def plugin_manager(self, plugin_manager):
		self.__plugin_manager = plugin_manager

class Settings(object):

	CATEGORY = "Settings"

	def __init__(self):
		super(Settings, self).__init__()

	def set_settings_value(self, section, name, value):
		pass

class SettingsProvider(object):

	CATEGORY = "SettingsProvider"

	def __init__(self):
		super(SettingsProvider, self).__init__()

	def on_settings_changed(self, section, name, value):
		pass

	def get_settings_content(self):
		pass

class SettingsUIProvider(object):

	CATEGORY = "SettingsUIProvider"

	def __init__(self):
		super(SettingsUIProvider, self).__init__()

	def get_settingsui_content(self):
		"""
		"""
		pass

class UserCache(object):
	"""
	"""

	CATEGORY = "UserCache"

	def __init__(self):
		super(UserCache, self).__init__()

	def add_pairing(self, user_id, player_id):
		"""
		"""
		pass

class VoiceClientListener(object):
	"""
	"""

	CATEGORY = "VoiceClientListener"

	def __init__(self):
		super(VoiceClientListener, self).__init__()

	def on_voice_client_connected(self):
		pass

	def on_current_voice_server_changed(self, server_id):
		pass

class VoiceClientProvider(object):
	"""
	"""

	CATEGORY = "VoiceClientProvider"

	def __init__(self):
		super(VoiceClientProvider, self).__init__()

	def get_my_connection_id(self):
		pass

class SnapshotProvider(object):
	"""
	"""

	CATEGORY = "SnapshotProvider"

	def __init__(self):
		super(SnapshotProvider, self).__init__()

	def create_snapshot(self):
		return "interface-invalid_snapshot"

	def release_snaphot(self, snapshot_name):
		pass

	def restore_snapshot(self, snapshot_name):
		pass
