import pybullet as p

def create_item(position, shape, size, color, baseMass=0.1):

    if shape == 'box':
        visual_shape = p.createVisualShape(
            p.GEOM_BOX,
            halfExtents=size,
            rgbaColor=color
        )
        collision_shape = p.createCollisionShape(
            p.GEOM_BOX,
            halfExtents=size
        )

    elif shape == 'sphere':
        visual_shape = p.createVisualShape(
            p.GEOM_SPHERE,
            radius=size[0],
            rgbaColor=color
        )
        collision_shape = p.createCollisionShape(
            p.GEOM_SPHERE,
            radius=size[0]
        )

    elif shape == 'cylinder':
        visual_shape = p.createVisualShape(
            p.GEOM_CYLINDER,
            radius=size[0],
            length=size[1],
            rgbaColor=color
        )
        collision_shape = p.createCollisionShape(
            p.GEOM_CYLINDER,
            radius=size[0],
            height=size[1]
        )

    else:
        raise ValueError(f"Unknown shape type: {shape}")

    body_id = p.createMultiBody(
        baseMass=baseMass,
        baseCollisionShapeIndex=collision_shape,
        baseVisualShapeIndex=visual_shape,
        basePosition=position
    )

    return body_id

def create_hollow_box(center_pos, width, length, height, thickness, color):
    """
    center_pos: [x, y, z] vị trí tâm mặt đáy
    width: chiều rộng (trục X)
    length: chiều dài (trục Y)
    height: chiều cao (trục Z)
    thickness: độ dày thành hộp
    """
    x, y, z = center_pos
    ids = []

    # 1. Mặt đáy (Bottom)
    ids.append(create_item(
        position=[x, y, z + thickness/2],
        shape='box',
        size=[width/2, length/2, thickness/2],
        color=color,
        baseMass=0 # Để hộp cố định, nếu muốn di chuyển hãy để > 0
    ))

    # 2. Thành hộp bên trái (Left Wall - dọc theo Y)
    ids.append(create_item(
        position=[x - width/2 + thickness/2, y, z + height/2],
        shape='box',
        size=[thickness/2, length/2, height/2],
        color=color,
        baseMass=0
    ))

    # 3. Thành hộp bên phải (Right Wall - dọc theo Y)
    ids.append(create_item(
        position=[x + width/2 - thickness/2, y, z + height/2],
        shape='box',
        size=[thickness/2, length/2, height/2],
        color=color,
        baseMass=0
    ))

    # 4. Thành hộp phía trước (Front Wall - dọc theo X)
    ids.append(create_item(
        position=[x, y + length/2 - thickness/2, z + height/2],
        shape='box',
        size=[width/2 - thickness, thickness/2, height/2],
        color=color,
        baseMass=0
    ))

    # 5. Thành hộp phía sau (Back Wall - dọc theo X)
    ids.append(create_item(
        position=[x, y - length/2 + thickness/2, z + height/2],
        shape='box',
        size=[width/2 - thickness, thickness/2, height/2],
        color=color,
        baseMass=0
    ))
    
    return ids