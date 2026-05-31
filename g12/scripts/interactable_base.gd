extends StaticBody3D

signal activated(state: bool)
signal interacted()

var is_activated: bool = false
var can_interact: bool = true

@export var order_index: int = 0
@export var highlight_color: Color = Color(1, 1, 0, 0.3)

@onready var meshes: Array = []
var original_colors: Dictionary = {}

func _ready():
	for child in get_children():
		if child is MeshInstance3D:
			meshes.append(child)
			if child.get_active_material(0):
				original_colors[child] = child.get_active_material(0).albedo_color

func interact(activator: Node):
	if not can_interact:
		return
	toggle()
	interacted.emit()

func toggle():
	is_activated = not is_activated
	activated.emit(is_activated)
	update_visual_state()

func set_state(new_state: bool):
	is_activated = new_state
	activated.emit(is_activated)
	update_visual_state()

func update_visual_state():
	pass

func set_highlight(highlight: bool):
	for mesh in meshes:
		if mesh.get_active_material(0):
			var mat = mesh.get_active_material(0)
			if highlight:
				mat.albedo_color = highlight_color
			elif original_colors.has(mesh):
				mat.albedo_color = original_colors[mesh]

func get_state_snapshot() -> Dictionary:
	return {
		"is_activated": is_activated,
		"can_interact": can_interact,
		"position": global_position,
		"rotation": global_rotation
	}

func restore_state_snapshot(state: Dictionary):
	is_activated = state.is_activated
	can_interact = state.can_interact
	global_position = state.position
	global_rotation = state.rotation
	update_visual_state()
	set_highlight(false)
