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

from gui.mods.tessumod import database
from gui.mods.tessumod.lib import logutils
from gui.mods.tessumod.messages import (BattlePlayerMessage, PrebattlePlayerMessage,
                                        UserMessage)
from gui.mods.tessumod.plugintypes import Plugin, SettingsProvider, UserCache

import pydash as _

import re
from copy import copy

logger = logutils.logger.getChild("usermatching")

def build_plugin():
	"""
	Called by plugin manager to build the plugin's object.
	"""
	return UserMatchingPlugin()

class UserMatchingPlugin(Plugin, SettingsProvider, UserCache):
	"""
	This plugin ...
	"""

	NS = "matching"

	def __init__(self):
		super(UserMatchingPlugin, self).__init__()
		self.__get_wot_nick_from_ts_metadata = True
		self.__ts_nick_search_enabled = True
		self.__nick_extract_patterns = []
		self.__name_mappings = {}

		self.__matchers = [
			self.__find_matching_with_metadata,
			self.__find_matching_with_patterns,
			self.__find_matching_with_mappings,
			self.__find_matching_with_name_comparison
		]

	@logutils.trace_call(logger)
	def initialize(self):
		self.messages.subscribe(BattlePlayerMessage, self.__on_player_event)
		self.messages.subscribe(PrebattlePlayerMessage, self.__on_player_event)
		self.messages.subscribe(UserMessage, self.__on_user_event)

	@logutils.trace_call(logger)
	def deinitialize(self):
		self.messages.unsubscribe(BattlePlayerMessage, self.__on_player_event)
		self.messages.unsubscribe(PrebattlePlayerMessage, self.__on_player_event)
		self.messages.unsubscribe(UserMessage, self.__on_user_event)

	@logutils.trace_call(logger)
	def on_settings_changed(self, section, name, value):
		"""
		Implemented from SettingsProvider.
		"""
		if section == "General":
			if name == "get_wot_nick_from_ts_metadata":
				self.__get_wot_nick_from_ts_metadata = value
			if name == "ts_nick_search_enabled":
				self.__ts_nick_search_enabled = value
			if name == "nick_extract_patterns":
				self.__nick_extract_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in value]
		if section == "NameMappings":
			self.__name_mappings[name.lower()] = value.lower()
		self.__match_users_to_players(database.get_live_users_in_my_channel(), database.get_live_players())

	@logutils.trace_call(logger)
	def get_settings_content(self):
		"""
		Implemented from SettingsProvider.
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
		database.insert_pairing(user_unique_id=user_id, player_id=player_id)

	@logutils.trace_call(logger)
	def __on_player_event(self, action, player):
		if action == "added":
			self.__match_users_to_players(database.get_live_users_in_my_channel(), [player])

	@logutils.trace_call(logger)
	def __on_user_event(self, action, user):
		if action in ["added", "modified"]:
			self.__match_users_to_players([user], database.get_live_players())

	def __match_users_to_players(self, users, players):
		for user, matching_players in self.__find_matching_candidates(users, players):
			for player in matching_players:
				self.add_pairing(user["unique_id"], player["id"])

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
		for player in players:
			if user["game_name"].lower() == player["name"].lower():
				results.append(player)
		return results

	def __find_matching_with_patterns(self, user, players):
		results = []
		if not self.__nick_extract_patterns:
			return results

		for pattern in self.__nick_extract_patterns:
			matches = pattern.match(user["name"].lower())
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
		playername = self.__name_mappings.get(user["name"].lower(), None)
		if playername is None:
			return []
		for player in players:
			if player["name"].lower() == playername:
				return [player]
		return []

	def __find_matching_with_name_comparison(self, user, players):
		results = []
		if self.__ts_nick_search_enabled:
			for player in players:
				if player["name"].lower() in user["name"].lower():
					results.append(player)
		else:
			for player in players:
				if player["name"].lower() == user["name"].lower():
					results.append(player)
		return results
