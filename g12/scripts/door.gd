extends StaticBody3D

@export var open_speed: float = 2.0
@export var open_distance: float = 2.5
@export var is_open: bool = false

var closed_position: Vector3
var target_position: Vector3

@onready var door_body: Node3D = $DoorBody

func _ready():
	closed_position = door_body.position
	target_position = closed_position

func _process(delta: float):
	door_body.position = door_body.position.lerp(target_position, open_speed * delta)

func open_door():
	if not is_open:
		is_open = true
		target_position = closed_position + Vector3(0, open_distance, 0)

func close_door():
	if is_open:
		is_open = false
		target_position = closed_position

func toggle():
	if is_open:
		close_door()
	else:
		open_door()
