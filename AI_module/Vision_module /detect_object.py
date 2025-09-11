import cv2
from ultralytics import YOLO

# Load model (có thể thay bằng yolov8s.pt, yolov8m.pt, ...)
model = YOLO("yolov8n.pt")

# Mở video thay vì webcam
video_path = "video_test.mp4"   # đổi thành file video của bạn
cap = cv2.VideoCapture(video_path)

while True:
    ret, frame = cap.read()
    if not ret:
        break  # hết video thì dừng

    # Detect
    results = model(frame)

    # Lấy thông tin bbox
    for r in results:
        boxes = r.boxes
        for box in boxes:
            # Tọa độ bounding box
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            label = model.names[cls]

            # Vẽ bbox
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{label} {conf:.2f}",
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow("YOLOv8 Detection", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
