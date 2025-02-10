import cv2
from ultralytics import YOLO
import numpy as np
import requests
import json
import os
import logging

logging.getLogger('ultralytics').setLevel(logging.ERROR)

class VehicleCounter:
    def __init__(self, video_path, model_path,backend_url,area_zone, config_file):
        # Initialize paths
        self.video_path = video_path
        self.model_path = model_path
        self.config_file = config_file
        self.backend_url = backend_url
        self.area_zone = area_zone
        
        # Initialize YOLO model
        try:
            self.model = YOLO(model_path)
        except Exception as e:
            print(f"Error loading YOLO model: {e}")
            raise
        
        # Initialize video capture
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise ValueError(f"Error opening video file: {video_path}")
        
        # Initialize first frame
        ret, frame = self.cap.read()
        if not ret:
            raise ValueError(f"Failed to read the first frame from the video: {self.video_path}")

        # Preprocess the first frame
        frame = cv2.GaussianBlur(frame, (5, 5), 0)  # Reduce Noise
        frame = cv2.convertScaleAbs(frame, alpha=1.2, beta=30)  # Adjust Contrast
        
        # Initialize counters and trackers
        self.car_out = 0
        self.car_trackers = {}
        self.next_car_id = 0
        self.car_passed = set()
        
        # Initialize UI elements
        self.roi_points = []
        self.car_line_out_start = None
        self.car_line_out_end = None
        self.drawing_roi = True
        
        # Configuration parameters
        self.object_threshold = 100  # Distance threshold for tracking
        self.confidence_threshold = 0.4  # YOLO confidence threshold
        
        # Load previous configuration if exists
        self.load_config()


    def load_config(self):
        """Load ROI and counting line configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.roi_points = [tuple(p) for p in config.get('roi_points', [])]
                    line_points = config.get('counting_line', {})
                    if line_points.get('start') and line_points.get('end'):
                        self.car_line_out_start = tuple(line_points['start'])
                        self.car_line_out_end = tuple(line_points['end'])
                print("Configuration loaded successfully")
            except Exception as e:
                print(f"Error loading configuration: {e}")
                self.reset_roi()

    def save_config(self):
        """Save current ROI and counting line configuration to file"""
        try:
            config = {
                
                'roi_points': [list(p) for p in self.roi_points],
                'counting_line': {
                    'start': list(self.car_line_out_start) if self.car_line_out_start else None,
                    'end': list(self.car_line_out_end) if self.car_line_out_end else None
                }
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
            print("Configuration saved successfully")
        except Exception as e:
            print(f"Error saving configuration: {e}")

    def reset_roi(self):
        """Reset ROI and counting line"""
        self.roi_points = []
        self.drawing_roi = True
        self.car_line_out_start = None
        self.car_line_out_end = None
        print("Reset ROI and counting line")

    def reset_counting_line(self):
        """Reset only the counting line"""
        self.car_line_out_start = None
        self.car_line_out_end = None
        print("Reset counting line")

    def is_crossing_line(self, prev_centroid, current_centroid):
        """Check if object crosses the counting line"""
        if not all([self.car_line_out_start, self.car_line_out_end, prev_centroid is not None]):
            return False
            
        line_vector = np.array(self.car_line_out_end) - np.array(self.car_line_out_start)
        line_normal = np.array([-line_vector[1], line_vector[0]])
        
        prev_distance = np.dot(prev_centroid - np.array(self.car_line_out_start), line_normal)
        current_distance = np.dot(current_centroid - np.array(self.car_line_out_start), line_normal)
        
        return prev_distance * current_distance < 0

    def process_click(self, x, y):
        """Process mouse click events"""
        if self.drawing_roi:
            self.roi_points.append((x, y))
            print(f"Added ROI point {len(self.roi_points)}: ({x}, {y})")
            
            if len(self.roi_points) >= 4:  # Changed to require exactly 4 points
                self.drawing_roi = False
                print("Switching to counting line mode")
        else:
            if self.car_line_out_start is None:
                self.car_line_out_start = (x, y)
                print(f"Set counting line start: ({x}, {y})")
            else:
                self.car_line_out_end = (x, y)
                print(f"Set counting line end: ({x}, {y})")

    def draw_interface(self, frame):
        """Draw ROI, counting line, and status information"""
        # Draw ROI
        if len(self.roi_points) > 0:
            pts = np.array(self.roi_points, np.int32)
            pts = pts.reshape((-1, 1, 2))
            cv2.polylines(frame, [pts], True, (0, 255, 255), 2)
            
            # Draw connecting lines
            for i in range(len(self.roi_points)):
                if i < len(self.roi_points) - 1:
                    cv2.line(frame, self.roi_points[i], self.roi_points[i+1], (0, 255, 255), 2)
            if len(self.roi_points) >= 3:
                cv2.line(frame, self.roi_points[-1], self.roi_points[0], (0, 255, 255), 2)

        # Draw counting line
        if self.car_line_out_start and self.car_line_out_end:
            cv2.line(frame, self.car_line_out_start, self.car_line_out_end, (0, 0, 255), 2)

        # Draw status information
        cv2.putText(frame, f"Cars Out: {self.car_out}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        status_text = "Drawing ROI" if self.drawing_roi else "Drawing Counting Line"
        cv2.putText(frame, status_text, (10, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

    def process_frame(self, frame):
        """Process a single frame"""
        if len(self.roi_points) < 4:
            return frame

        # Create ROI mask
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        roi_pts = np.array(self.roi_points, np.int32)
        cv2.fillPoly(mask, [roi_pts], 255)

        # Detect objects
        results = self.model(frame, conf=self.confidence_threshold)

        # Process detections
        car_centroids = []
        for result in results:
            for box in result.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                label = self.model.names[cls]

                if label in ["car", "bus", "truck"] and conf > self.confidence_threshold:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    centroid = np.array([(x1 + x2) / 2, (y1 + y2) / 2])
                    
                    # Check if centroid is in ROI
                    if cv2.pointPolygonTest(roi_pts, (centroid[0], centroid[1]), False) >= 0:
                        car_centroids.append(centroid)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Update trackers
        updated_car_trackers = {}
        for centroid in car_centroids:
            min_distance = float("inf")
            best_match_id = None

            for object_id, prev_centroid in self.car_trackers.items():
                distance = np.linalg.norm(prev_centroid - centroid)
                if distance < min_distance and distance < self.object_threshold:
                    min_distance = distance
                    best_match_id = object_id

            if best_match_id is None:
                updated_car_trackers[self.next_car_id] = centroid
                self.next_car_id += 1
            else:
                updated_car_trackers[best_match_id] = centroid

        # Check line crossings and draw tracks
        for object_id, centroid in updated_car_trackers.items():
            prev_centroid = self.car_trackers.get(object_id)
            
            if prev_centroid is not None:
                # Check line crossing
                if self.is_crossing_line(prev_centroid, centroid):
                    if object_id not in self.car_passed:
                        self.car_passed.add(object_id)
                        self.car_out += 1
                        print(f"Car {object_id} passed the line!")
                        self.send_data_to_backend()
                
                # Draw tracking line
                cv2.line(frame, tuple(prev_centroid.astype(int)), 
                        tuple(centroid.astype(int)), (255, 0, 0), 2)
            
            # Draw centroid and ID
            cv2.circle(frame, tuple(centroid.astype(int)), 4, (0, 255, 0), -1)
            cv2.putText(frame, f"ID: {object_id}", 
                    (int(centroid[0]) - 10, int(centroid[1]) - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        self.car_trackers = updated_car_trackers
        return frame
    
    def send_data_to_backend(self):
        if self.backend_url:
            payload = {
                "car_out": self.car_out,
                "area_zone": self.area_zone
                }
            headers = {"Content-Type": "application/json"}
        try:
            print(f"Sending data to backend: {payload}")
            response = requests.post(self.backend_url, json=payload, headers=headers)
            if response.status_code == 200:
                print(f"Data sent successfully! {self.car_out}")
            else:
                print(f"Failed to send data: {response.status_code}")
        except Exception as e:
            print(f"Error sending data: {e}")
            
    # cv2.namedWindow("Frame", cv2.WINDOW_NORMAL)  # อนุญาตให้ปรับขนาดหน้าต่างได้
    # cv2.resizeWindow("Frame", 720, 480)  # ปรับขนาดหน้าต่าง

    def run(self):
        """Main processing loop"""
        cv2.namedWindow("Vehicle Counter", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Vehicle Counter", 720, 480)
        
        def mouse_callback(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                self.process_click(x, y)
                
        cv2.setMouseCallback("Vehicle Counter", mouse_callback)

        try:
            while self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    print("End of video stream")
                    break

                processed_frame = self.process_frame(frame.copy())
                self.draw_interface(processed_frame)
                
                cv2.imshow("Vehicle Counter", processed_frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('e'):
                    self.reset_roi()
                elif key == ord('r'):
                    self.reset_counting_line()
                elif key == ord('s'):
                    self.save_config()
                    
        except Exception as e:
            print(f"Error in main loop: {e}")
        finally:
            self.cap.release()
            cv2.destroyAllWindows()
            

#ฟังก์ชันสำหรับส่งค่าไปยัง backend
# def send_data_to_backend(self):
#     url = "http://192.168.104.56:4050/Car_count"  # URL ของ API
#     # payload = {"car_out": car_count}  # ข้อมูลที่จะส่ง
#     headers = {"Content-Type": "application/json"}  # กำหนดประเภทข้อมูล
#     try:
#         response = requests.get(url, headers=headers)
#         if response.status_code == 200:
#             print("Data sent successfully!")
#         else:
#             print(f"Failed to send data: {response.status_code}")
#     except Exception as e:
#         print(f"Error sending data: {e}")

    # ตั้งค่าหน้าต่างและปรับขนาด
    # cv2.namedWindow("Frame", cv2.WINDOW_NORMAL)  # อนุญาตให้ปรับขนาดหน้าต่างได้
    # cv2.resizeWindow("Frame", 720, 480)  # ปรับขนาดหน้าต่าง
    
if __name__ == "__main__":
    # Configuration
    VIDEO_PATH = os.getenv("RTSP_PATH","Video/lkb-in.mp4") # แก้ไขเป็นพาธวิดีโอของคุณ
    MODEL_PATH = ("Model/yolov5mu.pt")   # แก้ไขเป็นพาธโมเดล YOLO ของคุณ
    BACKEND_URL = os.getenv("BACK_END_PATH","http://10.170.32.32:3000/Car_count")
    AREA_ZONE = os.getenv("AREA_ZONE","LKB-IN")
    CONFIG_NAME = os.getenv("CONFIG_FILE_NAME","LKB_IN.json")
    CONFIG_FILE_NAME = os.getenv("CONFIG_FILE_NAME","LKB-IN.json")
    # f"/Config/{CONFIG_NAME}"
    
    # http://192.168.102.105:8888/camera1/index.m3u8
    # ("rtsp://admin:iomc2024@192.168.102.110/LiveMedia/ch1/Media1")
    try:
        counter = VehicleCounter(VIDEO_PATH, MODEL_PATH,BACKEND_URL, AREA_ZONE,CONFIG_FILE_NAME)
        counter.run()
    except Exception as e:
        print(f"Application error: {e}")