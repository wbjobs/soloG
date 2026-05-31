extends Node3D

signal cutscene_started()
signal cutscene_finished()

var is_playing: bool = false
var current_shot: int = 0
var shots: Array = []
var original_camera: Camera3D = null

@onready var cutscene_camera: Camera3D = $CutsceneCamera

func play_cutscene(shot_list: Array):
	if is_playing or shot_list.size() == 0:
		return
	
	is_playing = true
	shots = shot_list.duplicate()
	current_shot = 0
	cutscene_started.emit()
	
	original_camera = get_viewport().get_camera_3d()
	cutscene_camera.current = true
	
	while current_shot < shots.size() and is_playing:
		var shot = shots[current_shot]
		current_shot += 1
		await play_shot(shot)
	
	if is_playing:
		finish_cutscene()

func play_shot(shot: Dictionary) -> Signal:
	var target_pos = shot.get("position", cutscene_camera.global_position)
	var target_look = shot.get("look_at", cutscene_camera.global_position + Vector3.FORWARD)
	var duration = shot.get("duration", 2.0)
	var easing = shot.get("easing", Tween.EASE_IN_OUT)
	var transition = shot.get("transition", Tween.TRANS_SINE)
	
	var start_pos = cutscene_camera.global_position
	var start_rot = cutscene_camera.global_rotation
	
	var tween = create_tween()
	tween.set_ease(easing)
	tween.set_trans(transition)
	
	tween.tween_method(
		func(t):
			cutscene_camera.global_position = start_pos.lerp(target_pos, t)
			var look_target = start_rot.slerp(_look_at_rotation(target_look, target_pos), t)
			cutscene_camera.global_rotation = look_target,
		0.0, 1.0, duration
	)
	
	return tween.finished

func _look_at_rotation(target: Vector3, from: Vector3) -> Vector3:
	var direction = (target - from).normalized()
	if direction.length() < 0.001:
		return Vector3.ZERO
	
	var yaw = atan2(direction.x, direction.z)
	var pitch = asin(clamp(-direction.y, -1.0, 1.0))
	return Vector3(pitch, yaw, 0)

func finish_cutscene():
	if original_camera:
		original_camera.current = true
	
	is_playing = false
	cutscene_finished.emit()

func skip():
	if not is_playing:
		return
	finish_cutscene()
