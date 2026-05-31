extends Node

const MAX_RECORD_SECONDS = 5.0
const RECORD_INTERVAL = 0.1

var is_recording: bool = true
var is_rewinding: bool = false

var state_history: Array = []
var record_timer: float = 0.0

@export var player: NodePath
@export var tracked_objects: Array[NodePath] = []

var player_ref: Node = null
var object_refs: Array[Node] = []

signal rewind_started()
signal rewind_finished()

func _ready():
	player_ref = get_node_or_null(player)
	for path in tracked_objects:
		var obj = get_node_or_null(path)
		if obj:
			object_refs.append(obj)

func _process(delta: float):
	if is_rewinding:
		return
	
	if is_recording:
		record_timer += delta
		if record_timer >= RECORD_INTERVAL:
			record_timer = 0.0
			record_state()
			trim_history()

func record_state():
	var state = {
		"time": Time.get_ticks_msec() / 1000.0,
		"player": {},
		"objects": []
	}
	
	if player_ref and player_ref.has_method("get_state_snapshot"):
		state.player = player_ref.get_state_snapshot()
	elif player_ref:
		state.player = {
			"position": player_ref.global_position,
			"rotation": player_ref.global_rotation
		}
	
	for obj in object_refs:
		var obj_state = {"node": obj}
		if obj.has_method("get_state_snapshot"):
			obj_state.data = obj.get_state_snapshot()
		else:
			obj_state.data = {
				"position": obj.global_position,
				"rotation": obj.global_rotation
			}
			if obj is RigidBody3D:
				obj_state.data.linear_velocity = obj.linear_velocity
				obj_state.data.angular_velocity = obj.angular_velocity
				obj_state.data.freeze = obj.freeze
		state.objects.append(obj_state)
	
	state_history.append(state)

func trim_history():
	var current_time = Time.get_ticks_msec() / 1000.0
	while state_history.size() > 0:
		var oldest = state_history[0]
		if current_time - oldest.time > MAX_RECORD_SECONDS:
			state_history.pop_front()
		else:
			break

func start_rewind():
	if is_rewinding or state_history.size() == 0:
		return
	
	is_rewinding = true
	is_recording = false
	rewind_started.emit()
	
	var target_state = state_history[0]
	
	if player_ref:
		if player_ref.has_method("restore_state_snapshot"):
			player_ref.restore_state_snapshot(target_state.player)
		else:
			player_ref.global_position = target_state.player.position
			player_ref.global_rotation = target_state.player.rotation
			if player_ref is CharacterBody3D:
				player_ref.velocity = Vector3.ZERO
	
	for obj_state in target_state.objects:
		var obj = obj_state.node
		if obj.has_method("restore_state_snapshot"):
			obj.restore_state_snapshot(obj_state.data)
		else:
			if obj is RigidBody3D:
				obj.freeze = true
				obj.global_position = obj_state.data.position
				obj.global_rotation = obj_state.data.rotation
				obj.linear_velocity = Vector3.ZERO
				obj.angular_velocity = Vector3.ZERO
				call_deferred("_restore_rigidbody", obj, obj_state.data)
			else:
				obj.global_position = obj_state.data.position
				obj.global_rotation = obj_state.data.rotation
	
	state_history.clear()
	record_timer = 0.0
	
	await get_tree().create_timer(0.15).timeout
	
	is_rewinding = false
	is_recording = true
	rewind_finished.emit()

func _restore_rigidbody(body: RigidBody3D, data: Dictionary):
	if not is_inside_tree():
		return
	body.freeze = data.freeze if "freeze" in data else false
	if "linear_velocity" in data:
		body.linear_velocity = data.linear_velocity
	if "angular_velocity" in data:
		body.angular_velocity = data.angular_velocity
