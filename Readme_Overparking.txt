# Overparking

ระบบนี้ใช้ YOLO ในการตรวจจับวัตถุเพื่อติดตามยานพาหนะในบริเวณที่ผู้ใช้กำหนด (ROI) และรายงานระยะเวลาที่รถจอดอยู่ พร้อมทั้งการเปลี่ยนแปลงสถานะ โดยสามารถเชื่อมต่อกับระบบ Backend เพื่อส่งการแจ้งเตือนได้

## คุณสมบัติ
- กำหนด ROI รูปหลายเหลี่ยมได้โดยการคลิกเมาส์
- ตรวจจับรถยนต์, รถบรรทุก, และรถบัสโดยใช้ YOLOv8
- อัปเดตสถานะแบบไดนามิก:  
  `ปกติ` → `น่าสงสัย` (5 วินาที) → `เตือน` (10 วินาที) → `อันตราย` (15 วินาที)
- บันทึกตำแหน่ง ROI ไว้ในไฟล์ JSON
- สามารถเชื่อมต่อกับระบบ Backend เพื่อส่งการแจ้งเตือน (ต้องทำการปรับแต่งเพิ่มเติม) 

## สิ่งที่ต้องติดตั้ง
- Python 3.8+
- OpenCV (`pip install opencv-python`)
- Ultralytics YOLO (`pip install ultralytics`)
- NumPy (`pip install numpy`)
- Requests (`pip install requests`)

##ติดตั้งไลบรารีที่จำเป็น:
pip 24.3.1 
pip install -r requirements.txt
ดาวน์โหลดโมเดล YOLOv8n (yolov8n.pt) และวางไว้ในโฟลเดอร์โปรเจค  self.model = YOLO(r"yolov8n.pt", verbose=False)  # ใช้ YOLOv8

##การใช้งาน
การตั้งค่า:แก้ไข VIDEO_PATH, CAMERA_NAME, และ LOCATION_NAME ในไฟล์
VIDEO_PATH = (r"ใส่ path vdo.mp4")  ถ้าใช้กล้องจริงสามารถใช้ RTSP ลงไปแทน ตัวอย่างของRTSP | rtsp://admin:Iomc%402024@10.170.32.2/LiveMedia/ch1/Media1
CAMERA_NAME = "ชื่อกล้อง"
LOCATION_NAME = "ชื่อสถานที่"

##การกำหนด ROI
คลิกเมาส์ 4 จุดเพื่อกำหนด ROI ของที่จอดรถ
กด s เพื่อบันทึก ROI
กด e เพื่อลบจุดที่กำลังวาดอยู่
ตำแหน่ง ROI จะถูกบันทึกอัตโนมัติในไฟล์ roi_points_overtime.json

##ปุ่มลัด
q: ออกจากโปรแกรม
s: บันทึก ROI
e: ลบจุดที่กำลังวาดอยู่

