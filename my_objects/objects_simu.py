import pybullet as p



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