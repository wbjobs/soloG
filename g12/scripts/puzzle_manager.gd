extends Node

signal puzzle_solved()
signal puzzle_failed()

@export var interactables: Array[Node] = []
@export var require_exact_order: bool = true

var current_step: int = 0
var solved: bool = false

func _ready():
	for i in range(interactables.size()):
		var obj = interactables[i]
		if obj.has_signal("interacted"):
			obj.interacted.connect(_on_interactable_used.bind(i))
		elif obj.has_signal("activated"):
			obj.activated.connect(_on_activated.bind(i))

func _on_interactable_used(index: int):
	if solved:
		return
	check_step(index)

func _on_activated(state: bool, index: int):
	if solved or not state:
		return
	check_step(index)

func check_step(index: int):
	if require_exact_order:
		if index == current_step:
			current_step += 1
			if current_step >= interactables.size():
				solved = true
				puzzle_solved.emit()
		else:
			reset_puzzle()
			puzzle_failed.emit()

func reset_puzzle():
	current_step = 0
	solved = false
	for obj in interactables:
		if obj.has_method("set_state"):
			obj.set_state(false)
