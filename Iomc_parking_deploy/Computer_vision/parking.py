import cv2
import requests
from ultralytics import YOLO
import numpy as np
import os
import time
import json
from collections import defaultdict

class VehicleCounter:
    def __init__(self, video_path, model_path, camera_name, location_name):
        self.video_path = video_path
        self.model_path = model_path
        self.camera_name = camera_name
        self.location_name = location_name
        self.roi_save_path = "roi_points.json"
        self.roi_save_path_2 = "roi_points_2.json"  # New ROI save path

        try:
            self.model = YOLO(model_path)
            self.model.overrides['verbose'] = False 
        except Exception as e:
            print(f"Error loading YOLO model: {e}")
            raise

        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise ValueError(f"Error opening video file: {video_path}")

        self.roi_points = self.load_roi_points(self.roi_save_path)
        self.roi_points_2 = self.load_roi_points(self.roi_save_path_2)  # Load new ROI points
        self.drawing_roi = len(self.roi_points) == 0
        self.drawing_roi_2 = len(self.roi_points_2) == 0  # New flag for drawing second ROI
        self.max_roi_points = 4

        self.confidence_threshold = 0.3 
        self.track_history = defaultdict(list)
        self.track_buffer = 20
        self.occlusion_threshold = 10
        self.last_vehicle_count = 0  # กำหนดค่าเริ่มต้นสำหรับการตรวจจับครั้งแรก

    def load_roi_points(self, path):
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    points = json.load(f)
                    if len(points) == 4:
                        return [(int(p[0]), int(p[1])) for p in points]
                    else:
                        print(f"Invalid ROI points in {path}. Starting fresh.")
                        return []
        except Exception as e:
            print(f"Error loading ROI points from {path}: {e}")
        return []

    def save_roi_points(self, path, points):
        try:
            if len(points) == 4:
                with open(path, 'w') as f:
                    json.dump(points, f)
                print(f"ROI points saved successfully to {path}")
        except Exception as e:
            print(f"Error saving ROI points to {path}: {e}")

    def is_in_roi(self, point):
        if len(self.roi_points) == 4:
            roi_pts = np.array(self.roi_points, np.int32)
            if cv2.pointPolygonTest(roi_pts.reshape((-1, 1, 2)), tuple(map(int, point)), False) >= 0:
                return True
        if len(self.roi_points_2) == 4:
            roi_pts_2 = np.array(self.roi_points_2, np.int32)
            if cv2.pointPolygonTest(roi_pts_2.reshape((-1, 1, 2)), tuple(map(int, point)), False) >= 0:
                return True
        return False

    def send_data_to_backend(self, vehicle_count):
        url = "http://192.168.100.70:3001/update-area-zone"
        #http://10.170.32.32:3001/update-area-zone
        payload = {
            "camera_name": self.camera_name,
            "area_zone": self.location_name,
            "total": vehicle_count
        }
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.put(url, json=payload, headers=headers)
            if response.status_code == 200:
                print("Data sent successfully!")
            else:
                print(f"Failed to send data: {response.status_code}")
        except Exception as e:
            print(f"Error sending data: {e}")

    def track_vehicles(self, frame):
        tracked_vehicles = {}
        results = self.model.track(frame, conf=self.confidence_threshold, persist=True, tracker="bytetrack.yaml")
        
        if results and len(results) > 0:
            boxes = results[0].boxes
            if hasattr(boxes, 'id') and boxes.id is not None:
                for box, track_id in zip(boxes, boxes.id):
                    track_id = int(track_id)
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    label = self.model.names[cls]

                    if label == "car" and conf > self.confidence_threshold:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        centroid = np.array([(x1 + x2) // 2, (y1 + y2) // 2])

                        if self.is_in_roi(centroid):
                            self.track_history[track_id].append(centroid)
                            if len(self.track_history[track_id]) > self.track_buffer:
                                self.track_history[track_id].pop(0)

                            tracked_vehicles[track_id] = {
                                'bbox': (x1, y1, x2, y2),
                                'centroid': centroid,
                                'label': label,
                                'conf': conf
                            }

        return tracked_vehicles

    def process_frame(self, frame):
        frame_copy = frame.copy()
        tracked_vehicles = self.track_vehicles(frame_copy)

        vehicle_count_in_roi = len(tracked_vehicles)

        for track_id, vehicle_data in tracked_vehicles.items():
            x1, y1, x2, y2 = vehicle_data['bbox']
            label = vehicle_data['label']
            conf = vehicle_data['conf']

            if conf >= self.confidence_threshold:
                color = (0, 255, 0)
                cv2.rectangle(frame_copy, (x1, y1), (x2, y2), color, 2)
                label_text = f"{label} #{track_id} {conf:.2f}"
                cv2.putText(frame_copy, label_text, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        if len(self.roi_points) > 0:
            pts = np.array(self.roi_points, np.int32)
            cv2.polylines(frame_copy, [pts.reshape((-1, 1, 2))], True, (255, 0, 0), 2)

        if len(self.roi_points_2) > 0:
            pts_2 = np.array(self.roi_points_2, np.int32)
            cv2.polylines(frame_copy, [pts_2.reshape((-1, 1, 2))], True, (255, 150, 0), 2)  # Different color for second ROI

        text = f"Vehicles in ROI: {vehicle_count_in_roi}"
        cv2.putText(frame_copy, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

        if self.last_vehicle_count != vehicle_count_in_roi:
            self.send_data_to_backend(vehicle_count_in_roi)
        self.last_vehicle_count = vehicle_count_in_roi

        return frame_copy

    def run(self):
        cv2.namedWindow("Vehicle Detection", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Vehicle Detection", 1280, 720)

        def mouse_callback(event, x, y, flags, param):
            if self.drawing_roi and event == cv2.EVENT_LBUTTONDOWN:
                if len(self.roi_points) < self.max_roi_points:
                    self.roi_points.append((x, y))
                    print(f"Point {len(self.roi_points)} added at ({x}, {y})")
                if len(self.roi_points) == self.max_roi_points:
                    print("All 4 points added for first ROI. Press 's' to save or 'c' to clear and start over.")
                    self.drawing_roi = False
                    self.drawing_roi_2 = True  # Start drawing second ROI

            elif self.drawing_roi_2 and event == cv2.EVENT_LBUTTONDOWN:
                if len(self.roi_points_2) < self.max_roi_points:
                    self.roi_points_2.append((x, y))
                    print(f"Point {len(self.roi_points_2)} added at ({x}, {y})")
                if len(self.roi_points_2) == self.max_roi_points:
                    print("All 4 points added for second ROI. Press 's' to save or 'c' to clear and start over.")
                    self.drawing_roi_2 = False

        cv2.setMouseCallback("Vehicle Detection", mouse_callback)

        try:
            ret, frame = self.cap.read()
            if not ret:
                print("Error: Cannot read the first frame.")
                return

            processed_frame = self.process_frame(frame)
            cv2.imshow("Vehicle Detection", processed_frame)

            self.send_data_to_backend(self.last_vehicle_count)

            while self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    print("End of video stream")
                    break

                processed_frame = self.process_frame(frame)
                cv2.imshow("Vehicle Detection", processed_frame)

                key = cv2.waitKey(10) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    self.save_roi_points(self.roi_save_path, self.roi_points)
                    self.save_roi_points(self.roi_save_path_2, self.roi_points_2)
                elif key == ord('c'):
                    self.roi_points.clear()
                    self.roi_points_2.clear()
                    self.drawing_roi = True
                    self.drawing_roi_2 = False
                    print("ROI points cleared.")
        finally:
            self.cap.release()
            cv2.destroyAllWindows()



if __name__ == "__main__":
    # Configuration
    VIDEO_PATH = "Video/LKB_IN_CAP01.mp4" #เปลี่ยนเป็นpath rtsp ของกล้องตัวที่ต้องการ ตัวอย่าง ("rtsp://admin:iomc2024@192.168.102.110/LiveMedia/ch1/Media1")
    MODEL_PATH = "Model/yolo11n.pt" #แนะนำใช้ YOLO: 5,8,11 เลือกใช้ตามสถานะการ
    CAMERA_NAME = "CAM01"  # เปลี่ยนเป็นชื่อที่ถูกต้องของกล้องนั้น
    LOCATION_NAME = "LKB-OUT" # เปลี่ยนเป็นชื่อที่ถูกต้องของสถานที่นั้น

    try:
        detector = VehicleCounter(VIDEO_PATH, MODEL_PATH, CAMERA_NAME, LOCATION_NAME)
        detector.run()
    except Exception as e:
        print(f"Error: {e}")
        