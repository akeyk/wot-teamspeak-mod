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

from gui.mods.tessumod import plugintypes, logutils, pluginutils, models
from gui.mods.tessumod.infrastructure.inifile import INIFile
from gui.mods.tessumod.infrastructure.gameapi import Environment
from BattleReplay import BattleReplay

import os
import json
import ConfigParser
import csv
import uuid
import itertools

logger = logutils.logger.getChild("usercache")

class UserCachePlugin(plugintypes.ModPlugin, plugintypes.SettingsMixin,
	plugintypes.SettingsUIProvider,	plugintypes.PlayerModelProvider,
	plugintypes.UserModelProvider, plugintypes.SnapshotProvider):
	"""
	This plugin ...
	"""

	def __init__(self):
		super(UserCachePlugin, self).__init__()
		self.__cached_player_model = models.Model()
		self.__cached_user_model = models.Model()
		self.__cached_player_model_proxy = models.ImmutableModelProxy(self.__cached_player_model)
		self.__cached_user_model_proxy = models.ImmutableModelProxy(self.__cached_user_model)
		self.__enabled_in_replays = False
		self.__in_replay = False
		self.__read_error = False
		self.__config_dirpath = os.path.join(Environment.find_res_mods_version_path(), "..", "configs", "tessumod")
		self.__cache_filepath = os.path.join(self.__config_dirpath, "usercache.json")
		self.__snapshots = {}
		BattleReplay.play = self.__hook_battlereplay_play(BattleReplay.play)

	@logutils.trace_call(logger)
	def initialize(self):
		self.__player_model = pluginutils.get_player_model(self.plugin_manager, ["battle", "prebattle", "clanmembers", "friends"])
		self.__user_model = pluginutils.get_user_model(self.plugin_manager, ["voice"])
		self.__pairing_model = self.plugin_manager.getPluginsOfCategory("UserCache")[0].plugin_object.get_pairing_model()
		self.__pairing_model.on("added", self.__on_pairings_changed)
		self.__pairing_model.on("modified", self.__on_pairings_changed)
		self.__pairing_model.on("removed", self.__on_pairings_changed)
		# create cache directory if it doesn't exist yet
		if not os.path.isdir(self.__config_dirpath):
			os.makedirs(self.__config_dirpath)
		# read cache file if it exists
		if self.__has_cache_file():
			self.__import_cache_structure(self.__load_cache_file())

	def migrate(self):
		"""
		Migrates old tessu_mod_cache.ini to a new format. Removes file if migration is successful.
		"""
		old_ini_filepath = os.path.join(Environment.find_res_mods_version_path(), "..", "configs", "tessu_mod", "tessu_mod_cache.ini")
		if os.path.isfile(old_ini_filepath):
			logger.info("Migrating old cache file: {0}".format(old_ini_filepath))
			with open(old_ini_filepath, "rb") as file:
				parser = ConfigParser.ConfigParser()
				parser.readfp(file)
				for name, id in parser.items("TeamSpeakUsers"):
					if id not in self.__cached_user_model:
						self.__cached_user_model.set({
							"id": id,
							"names": [name]
						})
				for name, id in parser.items("GamePlayers"):
					id = int(id)
					if id not in self.__cached_player_model:
						self.__cached_player_model.set({
							"id": id,
							"name": name
						})
				for user_name, player_names in parser.items("UserPlayerPairings"):
					for player_name in list(csv.reader([player_names]))[0]:
						for plugin_info in self.plugin_manager.getPluginsOfCategory("UserCache"):
							plugin_info.plugin_object.add_pairing(
								parser.get("TeamSpeakUsers", user_name),
								parser.getint("GamePlayers", player_name)
							)
			if self.__save_cache_file(self.__export_cache_structure()):
				# TODO: enable
				# os.remove(old_ini_filepath)
				pass

	@logutils.trace_call(logger)
	def deinitialize(self):
		# write to cache file
		self.__save_cache_file(self.__export_cache_structure())

	@logutils.trace_call(logger)
	def on_settings_changed(self, section, name, value):
		"""
		Implemented from SettingsMixin.
		"""
		if section == "General":
			if name == "update_cache_in_replays":
				self.__enabled_in_replays = value

	@logutils.trace_call(logger)
	def get_settings_content(self):
		"""
		Implemented from SettingsMixin.
		"""
		return {
			"General": {
				"help": "",
				"variables": [
					{
						"name": "update_cache_in_replays",
						"default": False,
						"help": """
							When turned on enables updating of tessu_mod_cache.ini when playing replays.
							Note that when playing someone else's replay your TS user will get paired
							with the replay's player name if this option is turned on.
							Useful for debugging purposes.
							Changing this value requires game restart.
						"""
					}
				]
			}
		}

	@logutils.trace_call(logger)
	def get_settingsui_content(self):
		"""
		Implemented from SettingsUIProvider.
		"""
		return {
			"General Settings": [
				{
					"label": "Save paired users in replay",
					"help": """
						When turned on enables updating of tessu_mod_cache.ini when playing replays.
						Note that when playing someone else's replay your TS user will get paired
						with the replay's player name if this option is turned on.
						Useful for debugging purposes.
						Changing this value requires game restart.
					""",
					"type": "checkbox",
					"variable": ("General", "update_cache_in_replays")
				}
			]
		}

	@logutils.trace_call(logger)
	def has_player_model(self, name):
		"""
		Implemented from PlayerModelProvider.
		"""
		return name == "cache"

	@logutils.trace_call(logger)
	def get_player_model(self, name):
		"""
		Implemented from PlayerModelProvider.
		"""
		assert name == "cache", "Plugin does not offer such model"
		return self.__cached_player_model_proxy

	@logutils.trace_call(logger)
	def has_user_model(self, name):
		"""
		Implemented from UserModelProvider.
		"""
		return name == "cache"

	@logutils.trace_call(logger)
	def get_user_model(self, name):
		"""
		Implemented from UserModelProvider.
		"""
		assert name == "cache", "Plugin does not offer such model"
		return self.__cached_user_model_proxy

	@logutils.trace_call(logger)
	def create_snapshot(self):
		"""
		Implemented from SnapshotProvider.
		"""
		snapshot_name = uuid.uuid4()
		self.__snapshots[snapshot_name] = self.__export_cache_structure()
		return snapshot_name

	@logutils.trace_call(logger)
	def release_snaphot(self, snapshot_name):
		"""
		Implemented from SnapshotProvider.
		"""
		if snapshot_name in self.__snapshots:
			del self.__snapshots[snapshot_name]

	@logutils.trace_call(logger)
	def restore_snapshot(self, snapshot_name):
		"""
		Implemented from SnapshotProvider.
		"""
		if snapshot_name in self.__snapshots:
			self.__import_cache_structure(self.__snapshots[snapshot_name])
			del self.__snapshots[snapshot_name]

	def __hook_battlereplay_play(self, orig_method):
		def wrapper(battlereplay_self, fileName=None):
			self.on_battle_replay()
			return orig_method(battlereplay_self, fileName)
		return wrapper

	@logutils.trace_call(logger)
	def on_battle_replay(self):
		self.__in_replay = True

	def __on_pairings_changed(self, *args, **kwargs):
		for pairing in self.__pairing_model.itervalues():
			self.__cache_user_id(pairing["id"])
			for player_id in pairing["player_ids"]:
				self.__cache_player_id(player_id)

	def __cache_user_id(self, user_id):
		if user_id in self.__user_model:
			self.__cached_user_model.set({
				"id": user_id,
				"names": self.__user_model[user_id]["names"][:1]
			})

	def __cache_player_id(self, player_id):
		if player_id in self.__player_model:
			self.__cached_player_model.set({
				"id": player_id,
				"names": self.__player_model[user_id]["name"]
			})

	def __has_cache_file(self):
		return os.path.isfile(self.__cache_filepath)

	def __load_cache_file(self):
		"""
		Reads cache file if it exists, returns loaded contents as object.
		"""
		try:
			with open(self.__cache_filepath, "rb") as file:
				return json.loads(file.read())
		except:
			self.__read_error = True
			raise

	def __save_cache_file(self, contents_obj):
		"""
		Writes current cache configuration to a file. Returns True on success, False on failure.
		"""
		if not self.__read_error and (not self.__in_replay or self.__enabled_in_replays):
			with open(self.__cache_filepath, "wb") as file:
				file.write(json.dumps(contents_obj, indent=4))
				return True
		return False

	def __import_cache_structure(self, cache_structure):
		assert cache_structure, "Cache content invalid"
		assert cache_structure.get("version") == 1, "Cache contents version mismatch"
		users = [{ "id": pairing[0]["id"], "names": set(pairing[0]["name"]) } for pairing in cache_structure["pairings"]]
		self.__cached_user_model.set_all(users)
		players = [{ "id": int(pairing[1]["id"]), "name": pairing[0]["name"] } for pairing in cache_structure["pairings"]]
		self.__cached_player_model.set_all(players)
		pairings = [(pairing[0]["id"], int(pairing[1]["id"])) for pairing in cache_structure["pairings"]]
		for plugin_info in self.plugin_manager.getPluginsOfCategory("UserCache"):
			plugin_info.plugin_object.reset_pairings(pairings)

	def __export_cache_structure(self):
		return {
			"version": 1,
			"pairings": list(itertools.chain(reduce(self.__reduce_pairing, self.__pairing_model.itervalues(), [])))
		}

	def __reduce_pairing(self, pairings, user):
		result = []
		user_name = list(self.__cached_user_model.get(user["id"], {}).get("names", [None]))[0]
		for player_id in user["player_ids"]:
			player_name = self.__cached_player_model.get(player_id, {}).get("name", None)
			result.append(({
				"id": user["id"],
				"name": user_name
			}, {
				"id": player_id,
				"name": player_name
			}))
		return pairings + result
