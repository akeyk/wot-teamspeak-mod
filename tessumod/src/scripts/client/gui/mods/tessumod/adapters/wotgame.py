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

import os
import xml.etree.ElementTree as ET

from ..infrastructure import gameapi
from ..infrastructure.timer import TimerMixin

from messenger.proto.events import g_messengerEvents
from PlayerEvents import g_playerEvents

class EnvironmentAdapter(object):

	def get_mods_dirpath(self):
		return gameapi.Environment.find_res_mods_version_path()

class BattleAdapter(TimerMixin):

	POSITIONAL_DATA_PROVIDE_TIMEOUT = 0.1

	def __init__(self, app):
		super(BattleAdapter, self).__init__()
		self.__app = app
		g_playerEvents.onAvatarBecomePlayer    += self.__on_avatar_become_player
		g_playerEvents.onAccountBecomePlayer   += self.__on_account_become_player
		g_playerEvents.onAvatarReady           += self.__on_avatar_ready
		g_playerEvents.onAvatarBecomeNonPlayer += self.__on_avatar_become_non_player
		g_messengerEvents.users.onUsersListReceived += self.__on_users_list_received
		gameapi.Battle.patch_battle_replay_play(self.__on_battle_replay_play)

	def get_camera_position(self):
		return gameapi.Battle.get_camera_position()

	def get_camera_direction(self):
		return gameapi.Battle.get_camera_direction()

	def get_vehicle(self, player_id):
		result = {}
		vehicle_id = gameapi.Battle.find_vehicle_id(lambda vehicle: vehicle["accountDBID"] == player_id)
		if vehicle_id is None:
			return result
		vehicle = gameapi.Battle.get_vehicle(vehicle_id)
		if vehicle:
			result["is-alive"] = vehicle.get("isAlive", True)
			entity = gameapi.Battle.get_entity(vehicle_id)
			if entity and entity.position:
				result["position"] = (entity.position.x, entity.position.y, entity.position.z)
		return result

	def __on_avatar_become_player(self):
		self.__app["publish-gamenick-to-chatserver"]()
		gameapi.Notifications.set_enabled(False)

	def __on_account_become_player(self):
		self.__app["publish-gamenick-to-chatserver"]()

	def __on_avatar_ready(self):
		self.__app["enable-positional-data-to-chatclient"](True)
		self.on_timeout(self.POSITIONAL_DATA_PROVIDE_TIMEOUT, self.__on_provide_positional_data, repeat=True)

	def __on_avatar_become_non_player(self):
		self.__app["enable-positional-data-to-chatclient"](False)
		self.off_timeout(self.__on_provide_positional_data)
		gameapi.Notifications.set_enabled(True)

	def __on_users_list_received(self, tags):
		self.__app["populate-usercache-with-players"]()

	def __on_provide_positional_data(self):
		self.__app["provide-positional-data-to-chatclient"]()

	def __on_battle_replay_play(self, original_self, original_method, *args, **kwargs):
		self.__app["battle-replay-start"]()
		return original_method(original_self, *args, **kwargs)

class PlayerAdapter(object):

	def get_player_by_dbid(self, dbid):
		return gameapi.Player.get_player_by_dbid(dbid)

	def get_my_name(self):
		return gameapi.Player.get_my_name()

	def get_my_dbid(self):
		return gameapi.Player.get_my_dbid()

	def get_players(self, in_battle=False, in_prebattle=False, clanmembers=False, friends=False):
		return gameapi.Player.get_players(in_battle, in_prebattle, clanmembers, friends)

class ChatIndicatorAdapter(object):

	def __init__(self):
		self.__speakers = set()
		gameapi.VoiceChat.patch_is_participant_speaking(self.__on_is_participant_speaking)

	def set_player_speaking(self, player, speaking):
		if speaking and player["id"] not in self.__speakers:
			self.__speakers.add(player["id"])
			gameapi.VoiceChat.set_player_speaking(player["id"], True)
		elif not speaking and player["id"] in self.__speakers:
			self.__speakers.remove(player["id"])
			gameapi.VoiceChat.set_player_speaking(player["id"], False)

	def clear_all_players_speaking(self):
		for speaker in self.__speakers:
			gameapi.VoiceChat.set_player_speaking(speaker, False)
		self.__speakers.clear()

	def __on_is_participant_speaking(self, original_self, original_method, dbid):
		'''Called by other game modules to determine current speaking status.'''
		return True if dbid in self.__speakers else original_method(original_self, dbid)

class MinimapAdapter(object):

	def __init__(self):
		self.__running_animations = {}
		self.__action = None
		self.__interval = None

	def set_action(self, action):
		self.__action = action

	def set_action_interval(self, interval):
		self.__interval = interval

	def set_player_speaking(self, player, speaking):
		if not player["in_battle"]:
			return
		vehicle_id = player["vehicle_id"]
		if speaking:
			if vehicle_id not in self.__running_animations:
				self.__running_animations[vehicle_id] = gameapi.MinimapMarkerAnimation(
					vehicle_id, self.__interval, self.__action, self.__on_done)
			self.__running_animations[vehicle_id].start()
		else:
			if vehicle_id in self.__running_animations:
				self.__running_animations[vehicle_id].stop()

	def clear_all_players_speaking(self):
		for vehicle_id in self.__running_animations:
			self.__running_animations[vehicle_id].stop()

	def __on_done(self, vehicle_id):
		self.__running_animations.pop(vehicle_id, None)

class NotificationsAdapter(object):

	TSPLUGIN_INSTALL  = "TessuModTSPluginInstall"
	TSPLUGIN_MOREINFO = "TessuModTSPluginMoreInfo"
	TSPLUGIN_IGNORED  = "TessuModTSPluginIgnore"

	def __init__(self, app):
		self.__app = app
		gameapi.Notifications.add_event_handler(self.TSPLUGIN_INSTALL, self.__on_plugin_install)
		gameapi.Notifications.add_event_handler(self.TSPLUGIN_IGNORED, self.__on_plugin_ignore_toggled)
		gameapi.Notifications.add_event_handler(self.TSPLUGIN_MOREINFO, self.__on_plugin_moreinfo_clicked)
		self.__plugin_install_shown = False

	def init(self):
		gameapi.Notifications.init()

	def show_info_message(self, message):
		gameapi.Notifications.show_info_message(message)

	def show_warning_message(self, message):
		gameapi.Notifications.show_warning_message(message)

	def show_error_message(self, message):
		gameapi.Notifications.show_error_message(message)

	def show_plugin_install_message(self, **data):
		if not self.__plugin_install_shown:
			tmpl_filepath = os.path.join(gameapi.Environment.find_res_mods_version_path(), "gui", "tessu_mod", "tsplugin_install_notification.xml")
			with open(tmpl_filepath, "r") as tmpl_file:
				params = self.__parse_xml(tmpl_file.read())

			gameapi.Notifications.show_custom_message(
				icon = params["icon"],
				message = params["message"],
				buttons_layout = params["buttons_layout"],
				item = {
					"moreinfo_url": "https://github.com/jhakonen/wot-teamspeak-mod/wiki/TeamSpeak-Plugins#tessumod-plugin",
					"ignore_state": "off",
					"install_action": self.TSPLUGIN_INSTALL,
					"ignore_action": self.TSPLUGIN_IGNORED,
					"moreinfo_action": self.TSPLUGIN_MOREINFO
				}
			)
			self.__plugin_install_shown = True

	def __parse_xml(self, xml_data):
		root = ET.fromstring(xml_data)
		params = {
			"icon": root.findtext("./icon", default=""),
			"message": self.__xml_element_contents_to_text(root.find("./message")),
			"buttons_layout": []
		}
		for button in root.findall("./buttonsLayout/button"):
			params["buttons_layout"].append({
				"label":  button.get("label", default=""),
				"action": button.get("action", default=""),
				"type":   button.get("type", default="submit")
			})
		return params

	def __xml_element_contents_to_text(self, element):
		if element is None:
			return ""
		contents = []
		contents.append(element.text or "")
		for sub_element in element:
			contents.append(ET.tostring(sub_element))
		contents.append(element.tail or "")
		return "".join(contents).strip()

	def __on_plugin_install(self, type_id, msg_id, data):
		self.__app["install-chatclient-plugin"]()

	def __on_plugin_ignore_toggled(self, type_id, msg_id, data):
		new_state = False if data["ignore_state"] == "on" else True
		data["ignore_state"] = "on" if new_state else "off"
		self.__app["ignore-chatclient-plugin-install-message"](new_state)
		gameapi.Notifications.update_custom_message(type_id, msg_id, data)

	def __on_plugin_moreinfo_clicked(self, type_id, msg_id, data):
		self.__app["show-chatclient-plugin-info-url"](data["moreinfo_url"])
