# TessuMod: Mod for integrating TeamSpeak into World of Tanks
# Copyright (C) 2014  Janne Hakonen
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

import ConfigParser
import os
import csv
import re
import io
from utils import LOG_ERROR, LOG_NOTE
import BigWorld
import Event

class UserCache(object):

	def __init__(self, ini_path):
		self._ts_users = {}
		self._players = {}
		self._pairings = {}
		self._ini_cache = INICache(ini_path)
		self._ini_cache.on_read += self._on_read
		self._ini_cache.on_write += self._on_write
		self._ini_cache.init()

	def _on_read(self, parser):
		pairings = {}
		for (player_nick,) in parser.items("PlayerUserPairings"):
			player_id = parser.getint("GamePlayers", player_nick)
			pairings[player_id] = [parser.getint("TeamSpeakUsers", ts_nick) for ts_nick in parser.getlist("PlayerUserPairings", player_nick)]
		ts_users = {id: nick for nick, id in parser.items("TeamSpeakUsers")}
		players = {id: nick for nick, id in parser.items("GamePlayers")}

		self._ts_users = ts_users
		self._players = players
		self._pairings = pairings

	def _on_write(self, parser):
		parser.add_section("TeamSpeakUsers")
		parser.add_section("GamePlayers")
		parser.add_section("PlayerUserPairings")
		for id in self._ts_users:
			parser.set("TeamSpeakUsers", self._ts_users[id], str(id))
		for id in self._players:
			parser.set("GamePlayers", self._players[id], str(id))
		for player_id in self._pairings:
			player_nick = self._players[player_id]
			ts_nicks = [self._ts_users[ts_id] for ts_id in self._pairings[player_id]]
			parser.set("PlayerUserPairings", player_nick, ts_nicks)

	def set_ini_check_interval(self, interval):
		self._ini_cache.ini_check_interval = interval

	def add_ts_user(self, user):
		LOG_NOTE("TS user: {0} ({1})".format(user.nick, user.unique_id))
		if user.unique_id not in self._ts_users:
			self._ts_users[user.unique_id] = user.nick
		self._ini_cache.write_needed()

	def add_player(self, player):
		LOG_NOTE("Player: {0} ({1})".format(player.getName(), player.getID()))
		if player.getID() not in self._players:
			self._players[player.getID()] = player.getName()
		self._ini_cache.write_needed()

class INICache(object):

	def __init__(self, ini_path):
		self._sync_time = 0
		self._parser = None
		self._check_interval = 5
		self._write_needed = False
		self._ini_path = ini_path
		self.on_read = Event.Event()
		self.on_write = Event.Event()

	def init(self):
		self._read_cache_file()
		self._write_cache_file()
		self._sync()

	@property
	def check_interval(self):
		return self._check_interval

	@check_interval.setter
	def ini_check_interval(self, interval):
		self._check_interval = interval

	def write_needed(self):
		self._write_needed = True

	def _read_cache_file(self):
		if not os.path.isfile(self._ini_path):
			return
		parser = ExtendedConfigParser()
		if not parser.read(self._ini_path):
			LOG_ERROR("Failed to parse ini file '{0}'"
				.format(self._ini_path))
			return
		self.on_read(parser)
		self._update_sync_time()

	def _update_sync_time(self):
		self._sync_time = self._get_modified_time()

	def _write_cache_file(self):
		parser = ExtendedConfigParser()
		self.on_write(parser)
		with open(self._ini_path, "w") as f:
			parser.write(f)
		self._update_sync_time()
		self._write_needed = False

	def _sync_cache_file(self):
		if self._is_cache_file_modified():
			self._read_cache_file()
		elif self._should_write_cache_file():
			self._write_cache_file()

	def _get_modified_time(self):
		return os.path.getmtime(self._ini_path)

	def _is_cache_file_modified(self):
		return self._sync_time < self._get_modified_time()

	def _should_write_cache_file(self):
		return self._write_needed or not os.path.isfile(self._ini_path)

	def _sync(self):
		self._sync_cache_file()
		BigWorld.callback(self.ini_check_interval, self._sync)

class ExtendedConfigParser(ConfigParser.SafeConfigParser):

	def getlist(self, section, option):
		return csv.reader([self.get(section, option)])[0]

	def set(self, section, option, value):
		if isinstance(value, list) or isinstance(value, tuple):
			string_io = io.StringIO()
			csv_out = csv.writer(string_io)
			csv_out.writerow(value)
			value = string_io.getvalue().rstrip("\r\n")
		ConfigParser.SafeConfigParser.set(self, section, option, value)
