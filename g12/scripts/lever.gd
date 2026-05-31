extends "res://scripts/interactable_base.gd"

@onready var lever_arm: Node3D = $LeverArm

func _ready():
	super._ready()
	update_visual_state()

func update_visual_state():
	if is_activated:
		lever_arm.rotation.x = -0.6
	else:
		lever_arm.rotation.x = 0.6
