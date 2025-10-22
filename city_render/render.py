import numpy as np
import trimesh
import pyrender
from PIL import Image
import importlib.resources as resources


with resources.files("city_render").joinpath("assets/road.stl").open("rb") as f:
    ROAD_TRIMESH = trimesh.load_mesh(f, "stl")

ROAD_VERTICAL = pyrender.Mesh.from_trimesh(ROAD_TRIMESH)




def render_city(city, filename="city_render.png", size=50):
    scene = pyrender.Scene(bg_color=[0.8, 0.9, 1.0, 1.0])

    # Build a green ground plane under the city
    all_positions = np.array([[b["x"], b["y"]] for b in city.city])
    min_xy = all_positions.min(axis=0) - 2
    max_xy = all_positions.max(axis=0) + 2
    center = (min_xy + max_xy) / 2
    spread = np.linalg.norm(max_xy - min_xy) * size

    ground_size = spread * 2
    ground = trimesh.creation.box(extents=(ground_size, ground_size, 0.05))
    ground.apply_translation([center[0], center[1], -0.025])
    ground_mat = pyrender.MetallicRoughnessMaterial(
        baseColorFactor=[0.2, 0.6, 0.2, 1.0],  # green
        roughnessFactor=1.0,
        metallicFactor=0.0
    )
    scene.add(pyrender.Mesh.from_trimesh(ground, material=ground_mat))

    roads = []

    SPACING = 1.6
    for b in city.city:
        x, y, h = b["x"], b["y"], b["height"]
        height = h * size

        world_x = x * size * SPACING
        world_y = y * size * SPACING

        # Add Building
        box = trimesh.creation.box(extents=(size, size, height))
        box.apply_translation([world_x, world_y, height / 2])
        box.visual.vertex_colors = np.tile([200, 200, 255, 255], (len(box.vertices), 1))
        box.fix_normals()

        mesh = pyrender.Mesh.from_trimesh(box)
        scene.add(mesh)

        # Add Roads
        for (dx1, dy1, dx2, dy2, is_vertical) in ((0, 0, 0, 1, True), (0, 0, 1, 0, False),
                                                  (1, 0, 1, 1, True), (0, 1, 1, 1, False)):
            tx1, ty1, tx2, ty2 = (x + dx1), (y + dy1), (x + dx2), (y + dy2)

            if (tx1, ty1, tx2, ty2) not in roads:
                if is_vertical:
                    # ROAD_VERTICAL = pyrender.Mesh.from_trimesh(ROAD_TRIMESH)
                    pass

                roads.append((tx1, ty1, tx2, ty2))

    # === LIGHTING ===
    for az in [0, 45, 90, 135, 180]:
        add_sun(scene, center, spread, elevation_deg=45, azimuth_deg=az, intensity=0.8)

    sky = pyrender.DirectionalLight(color=[0.7, 0.8, 1.0], intensity=0.4)
    sky_pose = np.eye(4)
    sky_pose[:3, 3] = [center[0], center[1], spread * 2.0]
    scene.add(sky, pose=sky_pose)

    # === CAMERA ===
    camera = pyrender.PerspectiveCamera(yfov=np.pi / 4.0)
    cam_pose = create_camera_pose(center, spread)
    scene.add(camera, pose=cam_pose)

    # === RENDER ===
    r = pyrender.OffscreenRenderer(1000, 800)
    color, _ = r.render(scene)
    r.delete()

    # Write to file
    Image.fromarray(color).save(filename)


def add_sun(scene, center, spread, elevation_deg=45, azimuth_deg=45, intensity=3.0):
    sun = pyrender.DirectionalLight(color=[1.0, 0.95, 0.85], intensity=intensity)

    elev = np.deg2rad(elevation_deg)
    azim = np.deg2rad(azimuth_deg)

    r = spread * 6.0
    x = center[0] + r * np.cos(elev) * np.cos(azim)
    y = center[1] + r * np.cos(elev) * np.sin(azim)
    z = center[1] + r * np.sin(elev)

    sun_pose = np.eye(4)
    sun_pose[:3, 3] = [x, y, z]

    dir_vec = np.array((*center, 0)) - np.array([x, y, z])
    dir_vec = dir_vec / np.linalg.norm(dir_vec)

    # Create rotation that makes -Z point along dir_vec
    up = np.array([0, 0, 1])
    right = np.cross(up, dir_vec)
    right /= np.linalg.norm(right)
    up = np.cross(dir_vec, right)

    rot = np.eye(4)
    rot[:3, :3] = np.stack([right, up, -dir_vec], axis=1)
    sun_pose = rot @ sun_pose

    scene.add(sun, pose=sun_pose)


def create_camera_pose(center, spread):
    eye = np.array([center[0] + spread * 0.8,
                    center[1] + spread * 0.8,
                    spread * 1.0])
    target = np.array([center[0], center[1], 0.0])

    up = np.array([0, 0, 1])
    forward = target - eye
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)

    pose = np.eye(4)
    pose[:3, :3] = np.stack([right, up, -forward], axis=1)
    pose[:3, 3] = eye
    return pose
