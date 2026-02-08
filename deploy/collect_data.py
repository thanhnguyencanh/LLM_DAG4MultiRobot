import os
import cv2
import time
from datetime import datetime
from camera import RealSenseCamera

# Configuration
SAVE_DIR = 'traindata'
CAMERA_ID = 943222070907  # Update with your camera ID


def main():
    # Create save directory
    os.makedirs(SAVE_DIR, exist_ok=True)

    # Initialize camera
    print("Connecting to camera...")
    camera = RealSenseCamera(device_id=CAMERA_ID)
    camera.connect()
    print("Camera connected!")

    print("\n=== Data Collection ===")
    print("Press 's' to save image")
    print("Press 'q' to quit")
    print(f"Images will be saved to: {os.path.abspath(SAVE_DIR)}/")
    print("=" * 25)

    img_count = len([f for f in os.listdir(SAVE_DIR) if f.endswith('.jpg')])
    print(f"Existing images: {img_count}")

    try:
        while True:
            # Get image
            bundle = camera.get_image_bundle()
            rgb = bundle['rgb']

            # Convert to BGR for display
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

            # Add info text
            display = bgr.copy()
            cv2.putText(display, f"Images saved: {img_count}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(display, "Press 's' to save, 'q' to quit", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            cv2.imshow('Data Collection', display)

            key = cv2.waitKey(1) & 0xFF

            if key == ord('s'):
                # Generate filename with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                filename = f"img_{timestamp}.jpg"
                filepath = os.path.join(SAVE_DIR, filename)

                # Save image (BGR format for cv2.imwrite)
                cv2.imwrite(filepath, bgr)
                img_count += 1
                print(f"Saved: {filename} (Total: {img_count})")

            elif key == ord('q'):
                print("\nQuitting...")
                break

    finally:
        cv2.destroyAllWindows()
        print(f"\nTotal images saved: {img_count}")


if __name__ == '__main__':
    main()
