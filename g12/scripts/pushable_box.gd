extends RigidBody3D

@export var push_force: float = 150.0
@export var box_mass: float = 40.0

var is_pushable: bool = true
var overlapping_bodies: Array[Node] = []

func _ready():
	mass = box_mass
	linear_damp = 0.85
	angular_damp = 1.5
	gravity_scale = 1.2
	contact_monitor = true
	max_contacts_reported = 16
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)

func get_mass() -> float:
	return box_mass

func _physics_process(delta: float):
	if not is_pushable:
		return
	
	for body in overlapping_bodies:
		if body is CharacterBody3D and body.velocity.length() > 0.1:
			var to_box = global_position - body.global_position
			to_box.y = 0
			var dist = to_box.length()
			
			if dist < 1.3:
				var move_dir = body.velocity.normalized()
				move_dir.y = 0
				var to_box_dir = to_box.normalized()
				var dot = move_dir.dot(to_box_dir)
				
				if dot > 0.15:
					var force_magnitude = push_force * delta * clamp(dot * 2.0, 0.5, 2.0)
					apply_central_force(move_dir * force_magnitude)
					
					if dot > 0.8 and dist < 0.8:
						var separation = to_box_dir * 0.02
						global_position += separation

func push(push_direction: Vector3, force_multiplier: float = 1.0):
	if not is_pushable:
		return
	var dir = push_direction.normalized()
	dir.y = 0
	apply_central_force(dir * push_force * force_multiplier * 0.1)

func get_state_snapshot() -> Dictionary:
	return {
		"position": global_position,
		"rotation": global_rotation,
		"linear_velocity": linear_velocity,
		"angular_velocity": angular_velocity,
		"freeze": freeze,
		"is_pushable": is_pushable
	}

func restore_state_snapshot(state: Dictionary):
	freeze = true
	global_position = state.position
	global_rotation = state.rotation
	linear_velocity = state.linear_velocity if "linear_velocity" in state else Vector3.ZERO
	angular_velocity = state.angular_velocity if "angular_velocity" in state else Vector3.ZERO
	freeze = state.freeze if "freeze" in state else false
	is_pushable = state.is_pushable if "is_pushable" in state else true

func _on_body_entered(body: Node):
	if not overlapping_bodies.has(body):
		overlapping_bodies.append(body)

func _on_body_exited(body: Node):
	if overlapping_bodies.has(body):
		overlapping_bodies.erase(body)
