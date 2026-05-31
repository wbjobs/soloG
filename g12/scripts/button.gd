extends "res://scripts/interactable_base.gd"

@onready var button_top: Node3D = $ButtonTop

func _ready():
	super._ready()
	update_visual_state()

func update_visual_state():
	if is_activated:
		button_top.position.y = 0.05
	else:
		button_top.position.y = 0.15
