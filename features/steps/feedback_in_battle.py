import random
import time

@given("WOT is running and in battle")
def step_impl(context):
	context.game.start()
	context.game.enter_battle()

@given("TS is connected to server")
def step_impl(context):
	context.ts_my_cid = random.randint(1, 255)
	context.ts_my_clid = random.randint(1, 255)
	context.ts_client.set_cmd_response("whoami",
		"clid={0} cid={1}".format(context.ts_my_clid, context.ts_my_cid))

@given("player \"{player_name}\" is in battle")
def step_impl(context, player_name):
	context.game.add_player(player_name)

@given("player \"{player_name}\" TS name is \"{ts_name}\" and has TessuMod installed")
def step_impl(context, player_name, ts_name):
	context.ts_to_player_name[ts_name] = player_name
	clid = context.ts_client.get_user_clid(ts_name)
	context.ts_client.set_cmd_response("clientgetuidfromclid clid={0}".format(clid),
		"notifyclientuidfromclid clid={0} nickname={1}".format(clid, ts_name.replace(" ", "\\s")))
	context.ts_client.set_cmd_response("clientvariable clid={0} client_meta_data".format(clid),
		"client_meta_data=<wot_nickname_start>{0}<wot_nickname_end>".format(player_name))

@given("TS user \"{ts_name}\" is speaking")
def step_impl(context, ts_name):
	clid = context.ts_client.get_user_clid(ts_name)
	context.ts_client.send_event("notifytalkstatuschange status=1 clid={0}".format(clid))
	# block execution until mod has detected the change
	context.game.is_player_speaking(context.ts_to_player_name[ts_name])

@when("TS user \"{ts_name}\" starts speaking")
def step_impl(context, ts_name):
	clid = context.ts_client.get_user_clid(ts_name)
	context.ts_client.send_event("notifytalkstatuschange status=1 clid={0}".format(clid))
	# block execution until mod has detected the change
	context.game.is_player_speaking(context.ts_to_player_name[ts_name])

@when("TS user \"{ts_name}\" stops speaking")
def step_impl(context, ts_name):
	clid = context.ts_client.get_user_clid(ts_name)
	context.ts_client.send_event("notifytalkstatuschange status=0 clid={0}".format(clid))
	# block execution until mod has detected the change
	context.game.is_player_not_speaking(context.ts_to_player_name[ts_name])

@then("I see speak feedback start for player \"{player_name}\"")
def step_impl(context, player_name):
	assert context.game.is_player_speaking(player_name)

@then("I see speak feedback end for player \"{player_name}\"")
def step_impl(context, player_name):
	assert context.game.is_player_not_speaking(player_name)
