extends Node3D

@onready var puzzle_manager: Node = $PuzzleManager
@onready var exit_door: Node = $ExitDoor
@onready var time_rewind: Node = $TimeRewind
@onready var cutscene_manager: Node = $CutsceneManager
@onready var player: Node = $Player
@onready var rewind_hint: Label = $UI/RewindHint

var played_cutscenes: Dictionary = {}

func _ready():
	puzzle_manager.puzzle_solved.connect(_on_puzzle_solved)
	time_rewind.rewind_started.connect(_on_rewind_started)
	time_rewind.rewind_finished.connect(_on_rewind_finished)
	cutscene_manager.cutscene_started.connect(_on_cutscene_started)
	cutscene_manager.cutscene_finished.connect(_on_cutscene_finished)

	var lever = get_node_or_null("Lever1")
	if lever and lever.has_signal("interacted"):
		lever.interacted.connect(_on_lever_triggered)

	var button = get_node_or_null("Button1")
	if button and button.has_signal("interacted"):
		button.interacted.connect(_on_button_triggered)

	var plate = get_node_or_null("PressurePlate1")
	if plate and plate.has_signal("activated"):
		plate.activated.connect(_on_plate_triggered)

func _unhandled_input(event: InputEvent):
	if event.is_action_pressed("rewind") and not time_rewind.is_rewinding and not cutscene_manager.is_playing:
		time_rewind.start_rewind()

func _on_rewind_started():
	player.can_control = false
	rewind_hint.visible = true

func _on_rewind_finished():
	player.can_control = true
	rewind_hint.visible = false
	played_cutscenes.clear()

func _on_cutscene_started():
	player.can_control = false

func _on_cutscene_finished():
	player.can_control = true

func _on_lever_triggered():
	if not played_cutscenes.get("lever", false):
		played_cutscenes.lever = true
		play_lever_cutscene()

func _on_button_triggered():
	if not played_cutscenes.get("button", false):
		played_cutscenes.button = true
		play_button_cutscene()

func _on_plate_triggered(state: bool):
	if state and not played_cutscenes.get("plate", false):
		played_cutscenes.plate = true
		play_plate_cutscene()

func play_lever_cutscene():
	var shots = [
		{
			"position": Vector3(-8, 3, -7),
			"look_at": Vector3(-8, 1, -10),
			"duration": 1.5
		},
		{
			"position": Vector3(-8, 2.5, -8.5),
			"look_at": Vector3(-8, 1.2, -10),
			"duration": 1.5
		}
	]
	cutscene_manager.play_cutscene(shots)

func play_button_cutscene():
	var shots = [
		{
			"position": Vector3(0, 3, -9),
			"look_at": Vector3(0, 1, -12),
			"duration": 1.5
		},
		{
			"position": Vector3(0, 2, -10.5),
			"look_at": Vector3(0, 0.5, -12),
			"duration": 1.5
		}
	]
	cutscene_manager.play_cutscene(shots)

func play_plate_cutscene():
	var shots = [
		{
			"position": Vector3(8, 3, -7),
			"look_at": Vector3(8, 1, -10),
			"duration": 1.5
		},
		{
			"position": Vector3(8, 1.5, -8.5),
			"look_at": Vector3(8, 0, -10),
			"duration": 1.5
		}
	]
	cutscene_manager.play_cutscene(shots)

func _on_puzzle_solved():
	exit_door.open_door()
	var shots = [
		{
			"position": Vector3(0, 3, -10),
			"look_at": Vector3(0, 1.5, -14.8),
			"duration": 2.0
		},
		{
			"position": Vector3(0, 2.5, -12),
			"look_at": Vector3(0, 1.5, -14.8),
			"duration": 2.0
		}
	]
	cutscene_manager.play_cutscene(shots)
