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

from gui.mods.tessumod import plugintypes, logutils, models, pluginutils
import re

logger = logutils.logger.getChild("usermatching")

# =============================================================================
#                          IMPLEMENTATION MISSING
#  - Snapshot interface
# =============================================================================

class UserMatching(plugintypes.ModPlugin, plugintypes.SettingsMixin, plugintypes.UserCache):
	"""
	This plugin ...
	"""

	def __init__(self):
		super(UserMatching, self).__init__()
		self.__get_wot_nick_from_ts_metadata = True
		self.__ts_nick_search_enabled = True
		self.__nick_extract_patterns = []
		self.__name_mappings = {}
		self.__user_model = None
		self.__all_player_model = None
		self.__pairing_model = models.Model()
		self.__pairing_model_proxy = models.ImmutableModelProxy(self.__pairing_model)

		self.__matchers = [
			self.__find_matching_with_metadata,
			self.__find_matching_with_patterns,
			self.__find_matching_with_mappings,
			self.__find_matching_with_name_comparison
		]


	@logutils.trace_call(logger)
	def initialize(self):
		self.__all_player_model = pluginutils.get_player_model(self.plugin_manager, ["battle", "prebattle"])
		self.__all_player_model.on("added", self.__on_all_player_model_added)
		self.__user_model = pluginutils.get_user_model(self.plugin_manager, ["voice"])
		self.__user_model.on("added", self.__on_user_added)
		self.__user_model.on("modified", self.__on_user_modified)

	@logutils.trace_call(logger)
	def deinitialize(self):
		pass

	@logutils.trace_call(logger)
	def on_settings_changed(self, section, name, value):
		"""
		Implemented from SettingsMixin.
		"""
		if section == "General":
			if name == "get_wot_nick_from_ts_metadata":
				self.__get_wot_nick_from_ts_metadata = value
			if name == "ts_nick_search_enabled":
				self.__ts_nick_search_enabled = value
			if name == "nick_extract_patterns":
				self.__nick_extract_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in value]
		if section == "NameMappings":
			self.__name_mappings = {k.lower(): v.lower() for k, v in value.iteritems()}
		self.__match_users_to_players(self.__user_model.values(), self.__all_player_model.values())

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
						"name": "get_wot_nick_from_ts_metadata",
						"default": True,
						"help": """
							Enables or disables WOT nickname fetching from speaking TS user's meta data.
							If disabled, matching TS user to WOT nickname relies only either TS nickname
							to be same as WOT nickname or extract patterns and name mappings to be able
							to convert TS nickname to WOT nickname.
							Useful for testing different extract patterns and name mappings.
							Use as follows:
							 1. Start one of your replays (from game's replays-folder)
							 2. Connect to TeamSpeak
							 3. Change your TS nickname to form you wish to test
							 4. Change this option to 'off'
							 5. Try talking and see if the speak notifications appear in-game.
							 6. If nothing happens, adjust 'nick_extract_patterns' and [NameMappings] options.
							 7. Jump back to step 5
						"""
					},
					{
						"name": "ts_nick_search_enabled",
						"default": True,
						"help": """
							Enables or disables searching of WOT player nicknames from within speaking TS
							user's nickname. With this option enabled you usually do not need to define
							anything in 'nick_extract_patterns' as the mod tries automatically to do the
							extracting for you.
							Disable this if the automatic searching pairs wrong TS users to wrong
							WOT players.
						"""
					},
					{
						"name": "nick_extract_patterns",
						"default": "",
						"help": """
							Defines regular expressions for extracting WOT nickname from user's
							TS nickname, e.g. if TS nickname is:
							  "wot_nickname | real name"
							Following expression will extract the wot_nickname:
							  nick_extract_patterns: ([a-z0-9_]+)
							For more info, see: https://docs.python.org/2/library/re.html
							The captured nickname is also stripped of any surrounding white space and
							compared case insensitive manner to seen WOT players.
							You can also define multiple patterns separated with commas (,). First
							pattern that matches will be used.
							As a more complex example, if you need to extract 'nick' from following
							TS nicknames:
							  nick [tag]
							  nick (tag)
							  nick (real name) [tag]
							  nick/real name [tag]
							  [tag] nick
							Use patterns:
							  nick_extract_patterns: ([a-z0-9_]+),\[[^\]]+\]\s*([a-z0-9_]+)
						"""
					}
				]
			},
			"NameMappings": {
				"help": """
					This section defines a mapping of users' TeamSpeak and WOT nicknames.
					Use TS nickname as key and WOT nickname as value.
					It is unnecessary define mapping for users who:
					 - have TessuMod already installed or
					 - have same name both in TS and WOT (matched case insensitive)
				""",
				"variables": "any",
				"variable_type": str
			}
		}

	@logutils.trace_call(logger)
	def add_pairing(self, user_id, player_id):
		"""
		Implemented from UserCache.
		"""
		if user_id not in self.__pairing_model:
			self.__pairing_model.set({ "id": user_id, "player_ids": set([player_id]) })
		else:
			pairing = dict(self.__pairing_model[user_id])
			pairing["player_ids"] |= set([player_id])
			self.__pairing_model.set(pairing)

	@logutils.trace_call(logger)
	def remove_pairing(self, user_id, player_id):
		"""
		Implemented from UserCache.
		"""
		if user_id in self.__pairing_model:
			pairing = dict(self.__pairing_model[user_id])
			pairing["player_ids"] -= set([player_id])
			self.__pairing_model.set(pairing)

	def reset_pairings(self, pairings):
		"""
		Implemented from UserCache.
		"""
		model_pairings_data = {}
		for pair in pairings:
			if pair[0] not in model_pairings_data:
				model_pairings_data[pair[0]] = {"id": pair[0], "player_ids": set()}
			model_pairings_data[pair[0]]["player_ids"].add(int(pair[1]))
		self.__pairing_model.set_all(model_pairings_data.values())

	@logutils.trace_call(logger)
	def get_pairing_model(self):
		"""
		Implemented from UserCache.
		"""
		return self.__pairing_model_proxy

	def __on_all_player_model_added(self, new_player):
		self.__match_users_to_players(self.__user_model.values(), [new_player])

	def __on_user_added(self, new_user):
		self.__match_users_to_players([new_user], self.__all_player_model.values())

	def __on_user_modified(self, old_user, new_user):
		if old_user["names"] != new_user["names"] or old_user["game_names"] != new_user["game_names"]:
			self.__match_users_to_players([new_user], self.__all_player_model.values())

	def __match_users_to_players(self, users, players):
		for user, matching_players in self.__find_matching_candidates(users, players):
			id = user["id"]
			for player in matching_players:
				self.add_pairing(id, player["id"])

	def __find_matching_candidates(self, users, players):
		results = []
		for user in users:
			for matcher in self.__matchers:
				matched_players = matcher(user, players)
				if matched_players:
					results.append((user, matched_players))
					break
		return results

	def __find_matching_with_metadata(self, user, players):
		results = []
		if not self.__get_wot_nick_from_ts_metadata:
			return results
		for usergamename in user["game_names"]:
			usergamename = usergamename.lower()
			for player in players:
				playername = player["name"].lower()
				if usergamename == playername:
					results.append(player)
		return results

	def __find_matching_with_patterns(self, user, players):
		results = []
		if not self.__nick_extract_patterns:
			return results

		for pattern in self.__nick_extract_patterns:
			for username in user["names"]:
				matches = pattern.match(username.lower())
				if matches is None or not matches.groups():
					continue
				extracted_playername = matches.group(1).strip()
				# find extracted playername from players
				for player in players:
					playername = player["name"].lower()
					if playername == extracted_playername:
						results.append(player)
		return results

	def __find_matching_with_mappings(self, user, players):
		results = []
		for username in user["names"]:
			username = username.lower()
			if username not in self.__name_mappings:
				return results
			playername = self.__name_mappings[username]
			for player in players:
				if player["name"].lower() == playername:
					return [player]
		return results

	def __find_matching_with_name_comparison(self, user, players):
		results = []
		for username in user["names"]:
			username = username.lower()
			if self.__ts_nick_search_enabled:
				for player in players:
					if player["name"].lower() in username:
						results.append(player)
			else:
				for player in players:
					if player["name"].lower() == username:
						results.append(player)
		return results
