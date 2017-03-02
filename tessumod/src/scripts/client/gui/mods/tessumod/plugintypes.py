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

class ModPlugin(object):

	CATEGORY = "Plugin"

	def __init__(self):
		super(ModPlugin, self).__init__()

	@property
	def plugin_manager(self):
		return self.__plugin_manager

	@plugin_manager.setter
	def plugin_manager(self, plugin_manager):
		self.__plugin_manager = plugin_manager

	def initialize(self):
		pass

	def deinitialize(self):
		pass

class SettingsMixin(object):

	CATEGORY = "Settings"

	def __init__(self):
		super(SettingsMixin, self).__init__()

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

	def remove_pairing(self, user_id, player_id):
		"""
		"""
		pass

	def reset_pairings(self, pairings):
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

class Notifications(object):
	"""
	"""

	CATEGORY = "Notifications"

	def __init__(self):
		super(Notifications, self).__init__()

	def show_notification(self, data):
		pass
