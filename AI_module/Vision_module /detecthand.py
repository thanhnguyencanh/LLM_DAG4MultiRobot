import cv2
import mediapipe as mp

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

def detect_hands_and_bboxes(frame, hands_detector):
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands_detector.process(img_rgb)

    h, w, _ = frame.shape
    output = []

    if not results.multi_hand_landmarks:
        return output, frame

    handedness_list = []
    if results.multi_handedness:
        for hand_h in results.multi_handedness:

            handedness_list.append(hand_h.classification[0].label)
    else:
        handedness_list = [None] * len(results.multi_hand_landmarks)

    for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
        lms = []
        xs = []
        ys = []
        for lm in hand_landmarks.landmark:
            lms.append((lm.x, lm.y, lm.z))
            xs.append(lm.x)
            ys.append(lm.y)

        xmin = max(0.0, min(xs))
        xmax = min(1.0, max(xs))
        ymin = max(0.0, min(ys))
        ymax = min(1.0, max(ys))

        x_px = int(xmin * w)
        y_px = int(ymin * h)
        x2_px = int(xmax * w)
        y2_px = int(ymax * h)
        bw = x2_px - x_px
        bh = y2_px - y_px

        entry = {
            'bbox': (x_px, y_px, bw, bh),
            'bbox_normalized': (xmin, ymin, xmax, ymax),
            'landmarks': lms,
            'handedness': handedness_list[idx] if idx < len(handedness_list) else None
        }
        output.append(entry)

        cv2.rectangle(frame, (x_px, y_px), (x2_px, y2_px), (0, 255, 0), 2)
        label = entry['handedness'] if entry['handedness'] else f'Hand {idx+1}'
        cv2.putText(frame, label, (x_px, max(10, y_px-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
        mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

    return output, frame


def main():
    cap = cv2.VideoCapture(0)

    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=4,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as hands:

        while True:
            ret, frame = cap.read()
            if not ret:
                print("Không đọc được camera")
                break

            bboxes, annotated = detect_hands_and_bboxes(frame, hands)

            if bboxes:
                print("Detected hands:", len(bboxes))
                for i, b in enumerate(bboxes):
                    print(f" Hand {i+1}: bbox (px) = {b['bbox']}, bbox_norm = {b['bbox_normalized']}, handedness = {b['handedness']}")

            cv2.imshow("Hand detection (press q to quit)", annotated)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
