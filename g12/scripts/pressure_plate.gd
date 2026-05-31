extends StaticBody3D

signal activated(state: bool)

var is_activated: bool = false
var required_mass: float = 10.0
var current_mass: float = 0.0

@onready var plate_top: Node3D = $PlateTop
@onready var area: Area3D = $Area3D

func _ready():
	area.body_entered.connect(_on_body_entered)
	area.body_exited.connect(_on_body_exited)
	update_visual_state()

func _on_body_entered(body: Node):
	if body.has_method("get_mass"):
		current_mass += body.get_mass()
	elif body is CharacterBody3D:
		current_mass += 70.0
	check_activation()

func _on_body_exited(body: Node):
	if body.has_method("get_mass"):
		current_mass -= body.get_mass()
	elif body is CharacterBody3D:
		current_mass -= 70.0
	current_mass = max(current_mass, 0.0)
	check_activation()

func check_activation():
	var new_state = current_mass >= required_mass
	if new_state != is_activated:
		is_activated = new_state
		activated.emit(is_activated)
		update_visual_state()

func update_visual_state():
	if is_activated:
		plate_top.position.y = 0.02
	else:
		plate_top.position.y = 0.08

func get_state_snapshot() -> Dictionary:
	return {
		"is_activated": is_activated,
		"current_mass": current_mass,
		"position": global_position,
		"rotation": global_rotation
	}

func restore_state_snapshot(state: Dictionary):
	is_activated = state.is_activated
	current_mass = state.current_mass if "current_mass" in state else 0.0
	global_position = state.position
	global_rotation = state.rotation
	update_visual_state()
