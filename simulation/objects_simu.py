import pybullet as p

def create_basket(base_position):
    basket_floor = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.2, 0.2, 0.01])
    basket_floor_id = p.createMultiBody(0, basket_floor, basePosition=base_position)

    wall_thickness = 0.005
    wall_height = 0.05
    half_size = 0.08

    wall_shape = p.createCollisionShape(p.GEOM_BOX, halfExtents=[half_size, wall_thickness, wall_height])

    walls = []

    walls.append(p.createMultiBody(0, wall_shape, basePosition=[base_position[0], base_position[1]-half_size, base_position[2]+wall_height]))
    walls.append(p.createMultiBody(0, wall_shape, basePosition=[base_position[0], base_position[1]+half_size, base_position[2]+wall_height]))
    walls.append(p.createMultiBody(0, wall_shape, basePosition=[base_position[0]-half_size, base_position[1], base_position[2]+wall_height], baseOrientation=p.getQuaternionFromEuler([0, 0, 1.57])))
    walls.append(p.createMultiBody(0, wall_shape, basePosition=[base_position[0]+half_size, base_position[1], base_position[2]+wall_height], baseOrientation=p.getQuaternionFromEuler([0, 0, 1.57])))

    basket_ids = [basket_floor_id] + walls
    return basket_ids, base_position


def create_item(position, shape, size, color):
    if shape == 'box':
        visual_shape = p.createVisualShape(p.GEOM_BOX, halfExtents=size, rgbaColor=color)
        collision_shape = p.createCollisionShape(p.GEOM_BOX, halfExtents=size)
    elif shape == 'sphere':
        visual_shape = p.createVisualShape(p.GEOM_SPHERE, radius=size[0], rgbaColor=color)
        collision_shape = p.createCollisionShape(p.GEOM_SPHERE, radius=size[0])
    elif shape == 'cylinder':
        visual_shape = p.createVisualShape(p.GEOM_CYLINDER, radius=size[0], length=size[1], rgbaColor=color)
        collision_shape = p.createCollisionShape(p.GEOM_CYLINDER, radius=size[0], height=size[1])

    return p.createMultiBody(
        baseMass=0.1,
        baseCollisionShapeIndex=collision_shape,
        baseVisualShapeIndex=visual_shape,
        basePosition=position
    )