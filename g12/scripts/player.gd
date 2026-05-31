extends CharacterBody3D

const SPEED = 4.5
const JUMP_VELOCITY = 4.5
const MOUSE_SENSITIVITY = 0.002
const INTERACTION_RANGE = 3.0

var gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")

@onready var camera: Node3D = $Camera3D
@onready var interaction_ray: RayCast3D = $Camera3D/InteractionRay

var current_interactable: Node = null
var can_control: bool = true

func _ready():
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _unhandled_input(event: InputEvent):
	if not can_control:
		return
	
	if event is InputEventMouseMotion:
		rotation.y -= event.relative.x * MOUSE_SENSITIVITY
		camera.rotation.x -= event.relative.y * MOUSE_SENSITIVITY
		camera.rotation.x = clamp(camera.rotation.x, -1.4, 1.4)
	
	if event is InputEventKey and event.keycode == KEY_ESCAPE:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	
	if event.is_action_pressed("interact"):
		interact()

func get_state_snapshot() -> Dictionary:
	return {
		"position": global_position,
		"rotation": global_rotation,
		"camera_rotation": camera.rotation,
		"velocity": velocity
	}

func restore_state_snapshot(state: Dictionary):
	global_position = state.position
	global_rotation = state.rotation
	if "camera_rotation" in state:
		camera.rotation = state.camera_rotation
	if "velocity" in state:
		velocity = state.velocity
	else:
		velocity = Vector3.ZERO

func _physics_process(delta: float):
	if not can_control:
		velocity.x = 0
		velocity.z = 0
		if not is_on_floor():
			velocity.y -= gravity * delta
		move_and_slide()
		return
	
	if not is_on_floor():
		velocity.y -= gravity * delta
	
	if Input.is_action_pressed("jump") and is_on_floor():
		velocity.y = JUMP_VELOCITY
	
	var input_dir: Vector2 = Input.get_vector("move_left", "move_right", "move_forward", "move_backward")
	var direction: Vector3 = Vector3.ZERO
	
	if input_dir != Vector2.ZERO:
		direction = (transform.basis * Vector3(input_dir.x, 0, input_dir.y)).normalized()
	
	velocity.x = direction.x * SPEED
	velocity.z = direction.z * SPEED
	
	move_and_slide()
	
	update_interaction()

func update_interaction():
	if interaction_ray.is_colliding():
		var collider = interaction_ray.get_collider()
		var distance = interaction_ray.get_collision_point().distance_to(camera.global_position)
		
		if distance <= INTERACTION_RANGE and collider.has_method("interact"):
			if current_interactable != collider:
				if current_interactable and current_interactable.has_method("set_highlight"):
					current_interactable.set_highlight(false)
				current_interactable = collider
				if current_interactable.has_method("set_highlight"):
					current_interactable.set_highlight(true)
		else:
			clear_interactable()
	else:
		clear_interactable()

func clear_interactable():
	if current_interactable and current_interactable.has_method("set_highlight"):
		current_interactable.set_highlight(false)
	current_interactable = null

func interact():
	if current_interactable and current_interactable.has_method("interact"):
		current_interactable.interact(self)
