import logging
import os
import cv2
import numpy as np
from ultralytics import YOLO
from camera import RealSenseCamera

logger = logging.getLogger(__name__)


class ObjectDetector:
    def __init__(self, camera, model_path='best.pt', calib_dir='saved_data'):
        """
        Initialize object detector with YOLO instance segmentation.

        Args:
            camera: RealSenseCamera instance.
            model_path: Path to YOLO segmentation model (trained on Roboflow).
            calib_dir: Directory containing calibration files.
        """
        self.camera = camera
        self.model = YOLO(model_path)
        self.calib_dir = calib_dir

        # Load calibration data
        self.camera2world = None
        self.depth_scale = 1.0
        self._load_calibration()

        # Log model classes
        logger.info(f"Model classes: {self.model.names}")

    def _load_calibration(self):
        """Load camera calibration data from files."""
        pose_file = os.path.join(self.calib_dir, 'camera_pose.txt')
        scale_file = os.path.join(self.calib_dir, 'camera_depth_scale.txt')

        if os.path.exists(pose_file):
            self.camera2world = np.loadtxt(pose_file)
            logger.info(f"Loaded camera pose from {pose_file}")
        else:
            logger.warning(f"Camera pose file not found: {pose_file}")
            self.camera2world = np.eye(4)

        if os.path.exists(scale_file):
            self.depth_scale = float(np.loadtxt(scale_file))
            logger.info(f"Loaded depth scale: {self.depth_scale}")
        else:
            logger.warning(f"Depth scale file not found: {scale_file}")

    def pixel_to_camera(self, pixel_x, pixel_y, depth):
        """Convert pixel coordinates to camera frame coordinates."""
        intrinsics = self.camera.intrinsics
        x = (pixel_x - intrinsics.ppx) * depth / intrinsics.fx
        y = (pixel_y - intrinsics.ppy) * depth / intrinsics.fy
        z = depth
        return np.array([x, y, z])

    def camera_to_world(self, point_camera):
        """Transform point from camera frame to world/robot frame (mm)."""
        point_h = np.append(point_camera, 1.0)
        point_world = self.camera2world @ point_h
        return point_world[:3] * 1000  # Convert to mm

    def pixel_to_world(self, pixel_x, pixel_y, depth):
        """Convert pixel coordinates directly to world coordinates (mm)."""
        depth_scaled = depth * self.depth_scale
        point_camera = self.pixel_to_camera(pixel_x, pixel_y, depth_scaled)
        return self.camera_to_world(point_camera)

    @staticmethod
    def parse_class_name(class_name):
        """
        Parse class name to extract color and object type.
        E.g., 'green_bowl' -> ('green', 'bowl')
             'red_cube' -> ('red', 'cube')
        """
        parts = class_name.lower().replace('-', '_').split('_')
        if len(parts) >= 2:
            color = parts[0]
            obj_type = '_'.join(parts[1:])
            return color, obj_type
        return None, class_name

    def detect_objects(self, conf_threshold=0.5, classes=None):
        """
        Detect objects using YOLO instance segmentation.

        Args:
            conf_threshold: Confidence threshold for detection.
            classes: List of class IDs to detect (None for all).

        Returns:
            list: List of detected objects with properties.
        """
        # Get image bundle
        bundle = self.camera.get_image_bundle()
        rgb = bundle['rgb']
        depth = bundle['aligned_depth'].squeeze()

        # Run YOLO detection
        results = self.model(rgb, conf=conf_threshold, classes=classes, verbose=False)

        detected_objects = []
        for result in results:
            boxes = result.boxes
            masks = result.masks

            if boxes is None:
                continue

            for i, box in enumerate(boxes):
                # Get bounding box
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                bbox = (x1, y1, x2, y2)

                # Get mask if available
                mask = None
                if masks is not None:
                    mask = masks.data[i].cpu().numpy()
                    if mask.shape != depth.shape:
                        mask = cv2.resize(mask, (rgb.shape[1], rgb.shape[0]),
                                         interpolation=cv2.INTER_NEAREST)

                # Get center pixel from mask centroid
                if mask is not None and np.any(mask > 0.5):
                    mask_binary = (mask > 0.5).astype(np.uint8)
                    M = cv2.moments(mask_binary)
                    if M['m00'] > 0:
                        center_x = int(M['m10'] / M['m00'])
                        center_y = int(M['m01'] / M['m00'])
                    else:
                        center_x = int((x1 + x2) / 2)
                        center_y = int((y1 + y2) / 2)
                else:
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)

                # Ensure within bounds
                center_x = np.clip(center_x, 0, depth.shape[1] - 1)
                center_y = np.clip(center_y, 0, depth.shape[0] - 1)

                # Get depth (median within mask for robustness)
                if mask is not None and np.any(mask > 0.5):
                    mask_binary = (mask > 0.5)
                    masked_depth = depth[mask_binary]
                    valid_depths = masked_depth[masked_depth > 0]
                    if len(valid_depths) > 0:
                        center_depth = np.median(valid_depths)
                    else:
                        center_depth = depth[center_y, center_x]
                else:
                    center_depth = depth[center_y, center_x]

                if center_depth <= 0:
                    logger.warning(f"Invalid depth at ({center_x}, {center_y})")
                    continue

                # Convert to world coordinates
                world_pos = self.pixel_to_world(center_x, center_y, center_depth)

                # Get class info
                class_id = int(box.cls[0])
                class_name = self.model.names[class_id]
                confidence = float(box.conf[0])

                # Parse color and type from class name
                color, obj_type = self.parse_class_name(class_name)

                obj_data = {
                    'class': class_name,
                    'type': obj_type,
                    'color': color,
                    'confidence': confidence,
                    'bbox': bbox,
                    'center_pixel': (center_x, center_y),
                    'depth': center_depth,
                    'position_world': world_pos,
                }

                if mask is not None:
                    obj_data['mask'] = mask

                detected_objects.append(obj_data)

        return detected_objects

    def get_object_position(self, class_name=None, color=None, obj_type=None, conf_threshold=0.5):
        """
        Get the world position of a specific object.

        Args:
            class_name: Full class name (e.g., 'green_bowl').
            color: Color to filter by (e.g., 'green', 'red', 'blue').
            obj_type: Object type to filter by (e.g., 'bowl', 'cube').
            conf_threshold: Confidence threshold.

        Returns:
            list or None: [x, y, z, roll, pitch, yaw] for robot, or None if not found.
        """
        objects = self.detect_objects(conf_threshold=conf_threshold)

        for obj in objects:
            if class_name and obj['class'] != class_name:
                continue
            if color and obj['color'] != color:
                continue
            if obj_type and obj['type'] != obj_type:
                continue

            pos = obj['position_world']
            return [pos[0], pos[1], pos[2], 180, 0, 0]

        return None

    def get_all_objects(self, conf_threshold=0.5):
        """
        Get all detected objects with their positions.

        Returns:
            dict: {class_name: [x, y, z, roll, pitch, yaw], ...}
        """
        objects = self.detect_objects(conf_threshold=conf_threshold)
        result = {}
        for obj in objects:
            pos = obj['position_world']
            result[obj['class']] = [pos[0], pos[1], pos[2], 180, 0, 0]
        return result

    def visualize(self, objects, show=True, show_masks=True):
        """Visualize detected objects with segmentation masks."""
        bundle = self.camera.get_image_bundle()
        rgb = bundle['rgb']
        vis = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        # Color map based on object color
        color_map = {
            'red': (0, 0, 255),
            'green': (0, 255, 0),
            'blue': (255, 0, 0),
        }

        for obj in objects:
            # Use actual object color for visualization
            vis_color = color_map.get(obj['color'], (255, 255, 0))

            x1, y1, x2, y2 = map(int, obj['bbox'])
            cx, cy = obj['center_pixel']
            pos = obj['position_world']

            # Draw segmentation mask
            if show_masks and 'mask' in obj and obj['mask'] is not None:
                mask = obj['mask']
                mask_binary = (mask > 0.5).astype(np.uint8)
                overlay = vis.copy()
                overlay[mask_binary == 1] = vis_color
                vis = cv2.addWeighted(vis, 0.7, overlay, 0.3, 0)
                contours, _ = cv2.findContours(mask_binary, cv2.RETR_EXTERNAL,
                                               cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(vis, contours, -1, vis_color, 2)
            else:
                cv2.rectangle(vis, (x1, y1), (x2, y2), vis_color, 2)

            # Draw center point
            cv2.circle(vis, (cx, cy), 5, (0, 0, 255), -1)

            # Draw labels
            label = f"{obj['class']} {obj['confidence']:.2f}"
            pos_label = f"[{pos[0]:.0f}, {pos[1]:.0f}, {pos[2]:.0f}]mm"
            cv2.putText(vis, label, (x1, y1 - 25), cv2.FONT_HERSHEY_SIMPLEX,
                       0.5, vis_color, 2)
            cv2.putText(vis, pos_label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX,
                       0.5, (255, 255, 0), 2)

        if show:
            cv2.imshow('Object Detection', vis)
            cv2.waitKey(1)

        return vis


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # Configuration
    CAMERA_ID = 943222070907
    MODEL_PATH = 'best.pt'

    # Initialize
    camera = RealSenseCamera(device_id=CAMERA_ID)
    camera.connect()

    detector = ObjectDetector(camera, model_path=MODEL_PATH)
    print(f"Model loaded: {MODEL_PATH}")
    print(f"Classes: {detector.model.names}")

    print("\n=== Controls ===")
    print("'q' - Quit")
    print("'p' - Print all object positions")
    print("'m' - Toggle mask display")
    print("================\n")

    show_masks = True

    try:
        while True:
            objects = detector.detect_objects(conf_threshold=0.5)
            detector.visualize(objects, show_masks=show_masks)

            if objects:
                print(f"\rDetected: {[obj['class'] for obj in objects]}", end='', flush=True)

            key = cv2.waitKey(100) & 0xFF
            if key == ord('q'):
                print("\nQuitting...")
                break
            elif key == ord('p'):
                print(f"\n--- Detected Objects ({len(objects)}) ---")
                for obj in objects:
                    print(f"  {obj['class']}: {obj['position_world']} (conf={obj['confidence']:.2f})")
            elif key == ord('m'):
                show_masks = not show_masks
                print(f"\nMask display: {'ON' if show_masks else 'OFF'}")
    finally:
        cv2.destroyAllWindows()
