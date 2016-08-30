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

import collections
from gui.mods.tessumod.infrastructure.eventemitter import EventEmitterMixin

class PlayerModel(collections.Mapping, EventEmitterMixin):

	def __init__(self):
		super(PlayerModel, self).__init__()
		self.__items = {}

	def set(self, item):
		id = item["id"]
		if id in self.__items:
			if item != self.__items[id]:
				old_item = self.__items[id]
				new_item = self.__items[id] = dict(item)
				self.emit("modified", old_item, new_item)
		else:
			self.__items[id] = dict(item)
			self.emit("added", item)

	def set_all(self, items):
		old_ids = set(self.items.keys())
		new_ids = set()
		for item in items:
			new_ids.add(item["id"])
			self.set(item)
		for missing_id in old_ids - new_ids:
			self.remove(missing_id)

	def remove(self, id):
		if id in self.__items:
			old_item = self.__items[id]
			del self.__items[id]
			self.emit("removed", old_item)

	def __getitem__(self, id):
		return self.__items[id]

	def __iter__(self):
		return iter(self.__items)

	def __len__(self):
		return len(self.__items)

class CompositeModel(collections.Mapping, EventEmitterMixin):

	def __init__(self, source_models):
		super(CompositeModel, self).__init__()
		self.__source_models = source_models
		self.__composite_items = {}
		for model in source_models:
			model.on("added", self.__on_source_model_added)
			model.on("modified", self.__on_source_model_modified)
			model.on("removed", self.__on_source_model_removed)

	def __on_source_model_added(self, new_item):
		id = new_item["id"]
		if id in self.__composite_items:
			old_composite_item = dict(self.__composite_items[id])
			self.__composite_items[id].update(new_item)
			if old_composite_item != self.__composite_items[id]:
				self.emit("modified", old_composite_item, self.__composite_items[id])
		else:
			self.__composite_items[id] = dict(new_item)
			self.emit("added", self.__composite_items[id])

	def __on_source_model_modified(self, old_item, new_item):
		id = old_item["id"]
		old_composite_item = dict(self.__composite_items[id])
		self.__composite_items[id].update(new_item)
		if old_composite_item != self.__composite_items[id]:
			self.emit("modified", old_composite_item, self.__composite_items[id])

	def __on_source_model_removed(self, old_item):
		id = old_item["id"]
		new_composite_item = {}
		for model in self.__source_models:
			new_composite_item.update(model.get(id, {}))
		if new_composite_item:
			if new_composite_item != self.__composite_items[id]:
				old_composite_item = self.__composite_items[id]
				self.__composite_items[id] = new_composite_item
				self.emit("modified", old_composite_item, new_composite_item)
		else:
			old_composite_item = self.__composite_items[id]
			del self.__composite_items[id]
			self.emit("removed", old_composite_item)

	def __getitem__(self, id):
		return self.__composite_items[id]

	def __iter__(self):
		for id, item in self.__composite_items.iteritems():
			yield id, item

	def __len__(self):
		return len(self.__composite_items)

class FilterModel(collections.Mapping, EventEmitterMixin):

	def __init__(self, source_model):
		super(FilterModel, self).__init__()
		self.__source_model = source_model
		self.__filtered_items = {}
		self.__filters = []
		source_model.on("added", self.__on_source_model_added)
		source_model.on("modified", self.__on_source_model_modified)
		source_model.on("removed", self.__on_source_model_removed)

	def add_filter(self, func):
		self.__filters.append(func)
		self.invalidate()

	def invalidate(self):
		for id, item in self.__source_model.iteritems():
			ok = self.__is_ok(item)
			if ok and id not in self.__filtered_items:
				self.__filtered_items[id] = dict(item)
				self.emit("added", self.__filtered_items[id])
			elif not ok and id in self.__filtered_items:
				del self.__filtered_items[id]
				self.emit("removed", item)

	def __on_source_model_added(self, new_item):
		id = new_item["id"]
		if self.__is_ok(new_item):
			self.__filtered_items[id] = new_item
			self.emit("added", new_item)

	def __on_source_model_modified(self, old_item, new_item):
		id = new_item["id"]
		ok = self.__is_ok(new_item)
		if id in self.__filtered_items:
			if ok:
				self.__filtered_items[id] = new_item
				self.emit("modified", old_item, new_item)
			else:
				del self.__filtered_items[id]
				self.emit("removed", old_item)
		else:
			if ok:
				self.__filtered_items[id] = new_item
				self.emit("added", new_item)

	def __on_source_model_removed(self, old_item):
		id = old_item["id"]
		if id in self.__filtered_items:
			del self.__filtered_items[id]
			self.emit("removed", old_item)

	def __is_ok(self, item):
		return all(f(item) for f in self.__filters)

	def __getitem__(self, id):
		return self.__filtered_items[id]

	def __iter__(self):
		return iter(self.__filtered_items)

	def __len__(self):
		return len(self.__filtered_items)
