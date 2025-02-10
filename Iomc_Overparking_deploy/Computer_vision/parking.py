import cv2
import numpy as np
import time
import json
import os
import requests
from datetime import datetime
from ultralytics import YOLO

class ParkingLotDetector:
    def __init__(self, video_path, camera_name, location_name):
        self.video_path = video_path
        self.camera_name = camera_name
        self.location_name = location_name
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise ValueError(f"Error opening video file: {video_path}")

        # โหลดโมเดล YOLO
        self.model = YOLO("Model/yolo11n.pt", verbose=False) 

        self.roi_points = []  # เก็บจุด ROI
        self.roi_list = []  # เก็บ ROI ที่บันทึกแล้ว [{id: int, points: [(x1, y1), ...], vehicles: {}}]
        self.current_roi_id = 0
        self.drawing_roi = True  # อยู่ในโหมดวาด ROI
        self.max_roi_points = 4  # จำนวนจุดสูงสุดของ ROI

        # เก็บข้อมูลรถที่จอด
        self.parked_vehicles = {}  # {roi_id: {'start_time': timestamp, 'status': status, 'image': frame}}

        # Create a directory to store images if it doesn't exist
        self.image_save_path = "parked_images"
        if not os.path.exists(self.image_save_path):
            os.makedirs(self.image_save_path)

    def save_roi_points(self):
        """บันทึกตำแหน่ง ROI ลงไฟล์"""
        try:
            with open("roi_points_overtime.json", "w") as f:
                json.dump(self.roi_list, f)
            print("ROI points saved successfully")
        except Exception as e:
            print(f"Error saving ROI points: {e}")

    def load_roi_points(self):
        """โหลดตำแหน่ง ROI จากไฟล์"""
        try:
            with open("roi_points_overtime.json", "r") as f:
                self.roi_list = json.load(f)
                self.current_roi_id = len(self.roi_list)
            print("ROI points loaded successfully")
        except Exception as e:
            print(f"Error loading ROI points: {e}")

    def is_bbox_in_roi(self, roi_points, bbox):
        """ตรวจสอบว่า Bounding Box อยู่ใน ROI หรือไม่"""
        x1, y1, x2, y2 = bbox
        centroid = ((x1 + x2) // 2, (y1 + y2) // 2)
        roi_pts = np.array(roi_points, np.int32)
        return cv2.pointPolygonTest(roi_pts.reshape((-1, 1, 2)), centroid, False) >= 0

    def process_frame(self, frame):
        """ประมวลผลแต่ละเฟรม"""
        frame_copy = frame.copy()

        # วาด ROI ที่บันทึกแล้ว
        for roi in self.roi_list:
            pts = np.array(roi['points'], np.int32)
            status = roi.get('status', 'normal')
            
            # เปลี่ยนสีเส้น ROI ตามสถานะ
            if status == 'normal':
                color = (0, 255, 0)  # สีเขียว
            elif status == 'suspicious':
                color = (0, 255, 255)  # สีเหลือง
            elif status == 'warning':
                color = (0, 165, 255)  # สีส้ม
            elif status == 'danger':
                color = (0, 0, 255)  # สีแดง

            cv2.polylines(frame_copy, [pts.reshape((-1, 1, 2))], True, color, 2)
            cv2.putText(frame_copy, f"ROI {roi['id']} - {status}", (pts[0][0], pts[0][1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # วาด ROI ที่กำลังวาด
        if self.drawing_roi:
            for i, point in enumerate(self.roi_points):
                cv2.circle(frame_copy, point, 5, (0, 0, 255), -1)
                if i > 0:
                    cv2.line(frame_copy, self.roi_points[i - 1], self.roi_points[i], (0, 0, 255), 2)

        return frame_copy

    def save_image_locally(self, roi_id, status, image):
        """Save image locally if status is suspicious, warning, or danger"""
        if image is not None and status in ['suspicious', 'warning', 'danger']:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"{roi_id}_{status}_{timestamp}.jpeg"
            image_path = os.path.join(self.image_save_path, image_filename)

            # Save the image locally
            cv2.imwrite(image_path, image)
            print(f"Image saved locally: {image_path}")
            return image_path

        return None

    def send_data_to_backend(self, roi_id, status, image=None):
        """Send data to the Backend"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = {
        "roi_id": roi_id,
        "status": status,
        "camera_name": self.camera_name,
        "location_name": self.location_name,
        "timestamp": timestamp
        }

        files = None
        if image is not None and status in ['suspicious', 'warning', 'danger']:
            _, buffer = cv2.imencode(".jpeg", image)
            files = {'image': ("image.jpeg", buffer.tobytes(), "image/jpeg")}

        response = requests.post("http://localhost:4050/over_parking", data=data, files=files)
        print(f"Sent data to backend: {response.status_code}, {response.text}")

    def run(self):
        """รันโปรแกรม"""
        cv2.namedWindow("Parking Lot Detection", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Parking Lot Detection", 1280, 720)

        def mouse_callback(event, x, y, flags, param):
            """Callback สำหรับการคลิกเมาส์"""
            if self.drawing_roi and event == cv2.EVENT_LBUTTONDOWN:
                if len(self.roi_points) < self.max_roi_points:
                    self.roi_points.append((x, y))
                    print(f"Point {len(self.roi_points)} added at ({x}, {y})")
                if len(self.roi_points) == self.max_roi_points:
                    print("All 4 points added. Press 's' to save or 'e' to clear and start over.")
                    self.roi_list.append({'id': self.current_roi_id, 'points': self.roi_points.copy()})
                    self.current_roi_id += 1
                    self.roi_points.clear()
                    self.save_roi_points()  # Save ROI points immediately after drawing

        cv2.setMouseCallback("Parking Lot Detection", mouse_callback)

        try:
            while self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    print("End of video stream")
                    break

                # ตรวจจับวัตถุด้วย YOLO
                results = self.model(frame, verbose=False)  # Suppress output
                vehicle_boxes = []
                for result in results:
                    boxes = result.boxes
                    for box in boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])  # รับค่าพิกัด Bounding Box
                        cls = int(box.cls[0])  # รับคลาสของวัตถุ
                        label = self.model.names[cls]  # รับชื่อคลาส
                        if label in ["car", "truck", "bus"]:
                            vehicle_boxes.append((x1, y1, x2, y2))

                # Process each ROI
                for roi in self.roi_list:
                    vehicle_in_roi = False
                    for (x1, y1, x2, y2) in vehicle_boxes:
                        if self.is_bbox_in_roi(roi['points'], (x1, y1, x2, y2)):
                            vehicle_in_roi = True
                            break

                    if vehicle_in_roi:
                        # อัปเดตสถานะและเวลา
                        if 'start_time' not in roi:
                            roi['start_time'] = time.time()
                            roi['status'] = 'normal'
                            self.send_data_to_backend(roi['id'], 'normal')
                        else:
                            elapsed_time = time.time() - roi['start_time']
                            if elapsed_time >= 15:
                                new_status = 'danger'
                            elif elapsed_time >= 10:
                                new_status = 'warning'
                            elif elapsed_time >= 5:
                                new_status = 'suspicious'
                            else:
                                new_status = 'normal'

                            if new_status != roi.get('status'):
                                roi['status'] = new_status
                                # ส่งข้อมูลพร้อมรูปภาพหากสถานะเปลี่ยน
                                if new_status in ['suspicious', 'warning', 'danger']:
                                    pts = np.array(roi['points'], np.int32)
                                    x, y, w, h = cv2.boundingRect(pts)
                                    roi_image = frame[y:y+h, x:x+w]
                                    self.send_data_to_backend(roi['id'], new_status, roi_image)
                                else:
                                    self.send_data_to_backend(roi['id'], new_status)
                    else:
                        # ไม่มียานพาหนะใน ROI, รีเซ็ตสถานะ
                        if 'start_time' in roi:
                            del roi['start_time']
                        if roi.get('status') != 'normal':
                            roi['status'] = 'normal'
                            self.send_data_to_backend(roi['id'], 'normal')

                processed_frame = self.process_frame(frame)
                cv2.imshow("Parking Lot Detection", processed_frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):  # ออกจากโปรแกรม
                    break
                elif key == ord('s'):  # บันทึก ROI
                    self.save_roi_points()
                elif key == ord('e'):  # ล้าง ROI ที่กำลังวาด
                    self.roi_points.clear()
                    print("ROI points cleared.")

        finally:
            self.cap.release()
            cv2.destroyAllWindows()


if __name__ == "__main__":
    # Configuration
    VIDEO_PATH = ("Video/LKB_IN_CAP01.mp4")
    CAMERA_NAME = "CAM01"
    LOCATION_NAME = "LKB_IN_POLE02"

    try:
        detector = ParkingLotDetector(VIDEO_PATH, CAMERA_NAME, LOCATION_NAME)
        detector.run()
    except Exception as e:
        print(f"Error: {e}")