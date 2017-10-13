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

from lib import pydash as _
from lib.littletable.littletable import Table, DataObject
from messages import (PlayerMeMessage, BattlePlayerMessage, VehicleMessage,
					  PrebattlePlayerMessage, PlayerSpeakingMessage,
					  UserMessage, PairingMessage)
from collections import Mapping

messages = None

_me_player = Table('me_player')
_me_player.create_index('id', unique=True)
_battle_players = Table('battle_players')
_battle_players.create_index('id', unique=True)
_vehicles = Table('vehicles')
_vehicles.create_index('id', unique=True)
_vehicles.create_index('player_id', unique=True)
_prebattle_players = Table('prebattle_players')
_prebattle_players.create_index('id', unique=True)
_speaking_players = Table('speaking_players')
_speaking_players.create_index('id', unique=True)
_users = Table('users')
_users.create_index('id', unique=True)
_users.create_index('unique_id')
_cached_users = Table('cached_users')
_cached_users.create_index('unique_id', unique=True)
_cached_players = Table('cached_players')
_cached_players.create_index('id', unique=True)
_pairings = Table('pairings')
_pairings.create_index('player_id')
_pairings.create_index('user_unique_id')


def get_my_player_id():
	player = _.head(_me_player)
	if player:
		return player.id

def get_my_vehicle():
	player = _.head(_me_player)
	if player:
		return _.head(_vehicles.where(player_id=player.id))

def get_player_vehicle(player_id):
	return _.head(_vehicles.where(player_id=player_id))

def get_user_paired_player_ids(user_unique_id):
	return _.pluck(_pairings.where(user_unique_id=user_unique_id), 'player_id')

def is_player_speaking(player_id):
	return bool(_speaking_players.where(id=player_id))

def get_user_id_vehicle_id_pairs():
	'''
	Joins _vehicles, _users and _pairings tables.
	Returns list of user_id and vehicle_id pairs.
	'''
	join1 = _pairings.join(_vehicles, [(_vehicles,'id','vehicle_id'), (_pairings,'user_unique_id')], player_id='player_id')
	join2 = join1.join(_users, [(join1,'vehicle_id'), (_users,'id','user_id')], user_unique_id='unique_id')
	return [(row.user_id, row.vehicle_id) for row in join2]

def upsert_live_user_to_cache(unique_id):
	user = _.head(_users.where(unique_id=unique_id))
	if user:
		remove_cached_user(unique_id=unique_id)
		insert_cached_user(unique_id=unique_id, name=user.name)

def upsert_live_player_to_cache(id):
	result = _battle_players.where(id=id)
	if not result:
		result = _prebattle_players.where(id=id)
	if not result:
		result = _me_player.where(id=id)
	player = _.head(result)
	if player:
		remove_cached_player(id=id)
		insert_cached_player(id=id, name=player.name)

def get_user_name(unique_id):
	result = _users.where(unique_id=unique_id)
	if not result:
		result = _cached_users.where(unique_id=unique_id)
	for row in result:
		if row.name:
			return row.name

def get_player_name(id):
	result = _battle_players.where(id=id)
	if not result:
		result = _prebattle_players.where(id=id)
	if not result:
		result = _me_player.where(id=id)
	if not result:
		result = _cached_players.where(id=id)
	for row in result:
		if row.name:
			return row.name

def get_live_users_in_my_channel():
	return _users.where(my_channel=True)

def get_live_players():
	players = _battle_players
	players = players.union(_prebattle_players.where(lambda o: o.id not in _.pluck(players, 'id')))
	players = players.union(_me_player.where(lambda o: o.id not in _.pluck(players, 'id')))
	return players

def get_all_pairings():
	return _pairings.clone()

def get_all_vehicles():
	return _vehicles.clone()

def set_me_player(id, name):
	_me_player.remove_many(_me_player)
	player = DataObject(id=id, name=name)
	_me_player.insert(player)
	messages.publish(PlayerMeMessage("added", player))

def insert_battle_player(id, name):
	if not _battle_players.where(id=id):
		player = DataObject(id=id, name=name)
		_battle_players.insert(player)
		messages.publish(BattlePlayerMessage("added", player))

def remove_battle_player(id):
	player = _.head(_battle_players.where(id=id))
	if player:
		_battle_players.remove(player)
		messages.publish(BattlePlayerMessage("removed", player))

def insert_vehicle(id, player_id, is_alive):
	if not _vehicles.where(id=id):
		vehicle = DataObject(id=id, player_id=player_id, is_alive=is_alive)
		_vehicles.insert(vehicle)
		messages.publish(VehicleMessage("added", vehicle))

def update_vehicle(id, player_id, is_alive):
	if _vehicles.delete(id=id):
		vehicle = DataObject(id=id, player_id=player_id, is_alive=is_alive)
		_vehicles.insert(vehicle)
		messages.publish(VehicleMessage("modified", vehicle))

def remove_vehicle(id):
	vehicle = _.head(_vehicles.where(id=id))
	if vehicle:
		_vehicles.remove(vehicle)
		messages.publish(VehicleMessage("removed", vehicle))

def insert_prebattle_player(id, name):
	if not _prebattle_players.where(id=id):
		player = DataObject(id=id, name=name)
		_prebattle_players.insert(player)
		messages.publish(PrebattlePlayerMessage("added", player))

def remove_prebattle_player(id):
	player = _.head(_prebattle_players.where(id=id))
	if player:
		_prebattle_players.remove(player)
		messages.publish(PrebattlePlayerMessage("removed", player))

def set_players_speaking(player_ids, speaking):
	for player_id in player_ids:
		old_player = _.head(_speaking_players.where(id=player_id))
		if speaking and not old_player:
			new_player = DataObject(id=player_id)
			_speaking_players.insert(new_player)
			messages.publish(PlayerSpeakingMessage("added", new_player))
		elif not speaking and old_player:
			_speaking_players.remove(old_player)
			messages.publish(PlayerSpeakingMessage("removed", old_player))

def insert_user(id, name, game_name, unique_id, speaking, is_me, my_channel):
	if _users.where(id=id):
		return
	new_user = DataObject(id=id, name=name, game_name=game_name,
		unique_id=unique_id, speaking=speaking, is_me=is_me,
		my_channel=my_channel)
	_users.insert(new_user)
	messages.publish(UserMessage("added", new_user))

def update_user(id, name, game_name, unique_id, speaking, is_me, my_channel):
	old_user = _.head(_users.where(id=id))
	if old_user:
		_users.remove(old_user)
		new_user = DataObject(id=id, name=name, game_name=game_name,
			unique_id=unique_id, speaking=speaking, is_me=is_me,
			my_channel=my_channel)
		_users.insert(new_user)
		messages.publish(UserMessage("modified", new_user))

def remove_user(id):
	old_user = _.head(_users.where(id=id))
	if not old_user:
		return
	_users.remove(old_user)
	messages.publish(UserMessage("removed", old_user))

def insert_cached_user(unique_id, name):
	_cached_users.insert(DataObject(unique_id=unique_id, name=name))

def remove_cached_user(unique_id):
	_cached_users.delete(unique_id=unique_id)

def insert_cached_player(id, name):
	_cached_players.insert(DataObject(id=id, name=name))

def remove_cached_player(id):
	_cached_players.delete(id=id)

def insert_pairing(user_unique_id, player_id):
	if not _pairings.where(user_unique_id=user_unique_id, player_id=player_id):
		pairing = DataObject(user_unique_id=user_unique_id, player_id=player_id)
		_pairings.insert(pairing)
		messages.publish(PairingMessage("added", pairing))

def remove_pairing(user_unique_id, player_id):
	pairing = _.head(_pairings.where(user_unique_id=user_unique_id, player_id=player_id))
	if pairing:
		_pairings.remove(pairing)
		messages.publish(PairingMessage("removed", pairing))
