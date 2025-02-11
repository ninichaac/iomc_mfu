ตำแหน่งไฟล์คำสัญ
Car_count
|
|----Backend
|       |--Dockerfile.js
|       |--server.js
|       |--.env(Dev)
|
|----Cemera
|       |--Dockerfile
|       |--Car_counting.py
|
|-Dockerfile.base
|-Docker-compose
|-.env(Deploy)
|-requirment.txt
|







-----------------------------------------------




องค์ประกอบที่ต้องการ

Node.js 
MySQL(post 3306)
python 3.12.10

&&&&&&&&.env(ที่อยู่ใน directory Backend):&&&&&&&&



DB_HOST= localhost            # Host machine's IP for the MySQL database
DB_PORT= 3306                 # MySQL port
DB_USER= root                 # MySQL username
DB_PASSWORD= 1234             # MySQL password
DB_NAME= smartparking         # MySQL database name



&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&









-----------------------------------------------




Dev:
เปิดครั้งแรก:-cd สู่ directory Backend "npm install"
	 -cd สู่ directory Camera สร้าง .venv แล้ว copy requirment.txt จากข้าง directory "Car_count" นำมา pip install -r requirment.txt

หาก dev ให้เปิดใช้ terminal 2 อัน 

อันที่ 1 cd สู่ directory Backend แล้ว "node sever.js"
อันที่ 2 cd cd สู่ directory Camera "python Car_counting.py"










-----------------------------------------------

Docker

-ใช้ command "docker build -t my-python-base -f Dockerfile.base ." สร้าง images my-python-base สำหรับ dockerfile ของ directory Camera
-ใช้คำสั่ง "docker-compose -p iomc up -d"


&&&&&&&&.env(ที่อยู่ใน directory Backend):&&&&&&&&



DB_HOST= host.docker.internal # Host machine's IP for the MySQL database(for windows)
DB_PORT= 3306                 # MySQL port
DB_USER= root                 # MySQL username
DB_PASSWORD= 1234             # MySQL password
DB_NAME= smartparking         # MySQL database name



&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&



*********importent********

เราใช้ MySQL ที่อยู่ใน localmechanic(ไม่ใช้ใน docker)

หากเป็น Linux ต้องใช้คำสั่ง "sudo ip addr add 192.168.1.100/24 dev docker0"
และเปลี่ยน "DB_HOST= host.docker.internal" เป็น "DB_HOST= 192.168.1.100"


**************************

ตอน deploy ขึ้นเซิฟใช้วิธี  build image แล้ว "docker save -o iomc.tar my-python-base:latest" และ .tar ของ node ส่งขึ้นเซิฟ แก้ไข docker-compose ให้ใช้ images ในการ build container แทน





ปัญหาคือไม่สามารถเปิด video analytic ใน container ได้ เพราะหา display=0 ไม่เจอ **เคยทำ docker แบบเต็มระบบที่ ubuntu ของบริษัทได้ ** แต่ deploy ขึ้นเซิฟแล้วเปิดไม่ได้(สาเหตุ คาดว่าเพราะคอมเซิฟไม่ได้ต่อจอไว้ จึงน่าจะทำแบบ off-screen ได้ )





-----------------------------------------------





Python

โค้ดนี้เป็นระบบตรวจจับและนับจำนวนรถจากวิดีโอโดยใช้ YOLO + OpenCV ซึ่งสามารถกำหนด ROI และเส้นนับจำนวนรถได้เอง และส่งข้อมูลไปยังเซิร์ฟเวอร์ Backend เพื่อใช้ในการวิเคราะห์ต่อไป

1. องค์ประกอบหลักของโปรแกรม
โปรแกรมนี้ทำหน้าที่ตรวจนับจำนวนรถที่ผ่านบริเวณที่กำหนดในวิดีโอ โดยมีองค์ประกอบหลักดังนี้:
-การใช้ YOLO (You Only Look Once) เพื่อตรวจจับยานพาหนะ
-การประมวลผลภาพด้วย OpenCV สำหรับวาดเส้นเขตและแสดงผลข้อมูล
-การติดตามและนับจำนวนรถที่ผ่านเส้นกำหนด
-การส่งข้อมูลไปยังเซิร์ฟเวอร์ Backend ผ่าน HTTP API

2. หลักการทำงาน
-โหลดโมเดล YOLO และวิดีโอ
-โหลดโมเดล YOLO จากพาธที่กำหนด
-เปิดไฟล์วิดีโอเพื่อนำภาพมาประมวลผล
-กำหนดจุด ROI (Region of Interest) และเส้นนับจำนวนรถ
-ให้ผู้ใช้คลิกเพื่อกำหนดพื้นที่ตรวจจับและเส้นที่ใช้วัดว่ารถผ่านไปแล้ว
-ตรวจจับรถและติดตามการเคลื่อนที่
-ใช้ YOLO ตรวจจับรถในเฟรม
-คำนวณตำแหน่ง centroid ของรถแต่ละคัน
-ใช้ระยะทางของ centroid เพื่อติดตามวัตถุระหว่างเฟรม
-ตรวจสอบการผ่านเส้นนับจำนวน
-หาก centroid เปลี่ยนตำแหน่งจากฝั่งหนึ่งของเส้นไปยังอีกฝั่ง แสดงว่ารถผ่านเส้น
-เพิ่มค่าตัวแปร car_out เพื่อบันทึกจำนวนรถที่ออก
-ส่งข้อมูลไปยัง Backend
-ส่งค่าจำนวนรถออกไปยังเซิร์ฟเวอร์ผ่าน API ที่กำหนด

3. ฟังก์ชันที่สำคัญ
ฟังก์ชันเกี่ยวกับการตั้งค่าและโหลดข้อมูล
-load_config() : โหลดค่าการตั้งค่า ROI และเส้นนับจำนวนจากไฟล์
-save_config() : บันทึกค่าการตั้งค่า ROI และเส้นนับจำนวนไปยังไฟล์
-reset_roi() : รีเซ็ตค่าขอบเขต ROI
-reset_counting_line() : รีเซ็ตเส้นนับจำนวน
ฟังก์ชันเกี่ยวกับการประมวลผลวิดีโอ
-process_click(x, y) : รับค่าจุดที่ผู้ใช้คลิกเพื่อกำหนด ROI และเส้นนับจำนวน
-draw_interface(frame) : วาดเส้น ROI, เส้นนับจำนวน และแสดงจำนวนรถ
-process_frame(frame) : ประมวลผลเฟรมวิดีโอเพื่อตรวจจับรถ, ติดตามการเคลื่อนที่ และนับจำนวน
ฟังก์ชันเกี่ยวกับการตรวจจับและนับรถ
-is_crossing_line(prev_centroid, current_centroid) : ตรวจสอบว่ารถข้ามเส้นนับจำนวนหรือไม่
-send_data_to_backend() : ส่งข้อมูลจำนวนรถที่นับได้ไปยังเซิร์ฟเวอร์ Backend
ฟังก์ชันหลัก
-run() : ลูปหลักของโปรแกรมที่ดึงเฟรมจากวิดีโอ, ตรวจจับรถ, นับจำนวน และแสดงผล

4. ตัวแปรที่เป็น Config
-VIDEO_PATH : พาธของวิดีโอที่ใช้ตรวจจับรถ
-MODEL_PATH : พาธของโมเดล YOLO
-BACKEND_URL : URL ของ Backend ที่ใช้ส่งข้อมูล
-AREA_ZONE : รหัสโซนพื้นที่ที่ตรวจนับรถ
-CONFIG_FILE_NAME : พาธไฟล์ที่เก็บค่าตั้งค่าของ ROI และเส้นนับจำนวน
-object_threshold : ค่าระยะห่างสูงสุดสำหรับการจับคู่วัตถุในเฟรมถัดไป
-confidence_threshold : ค่าความมั่นใจขั้นต่ำของ YOLO ในการตรวจจับรถ

5. Library ที่ใช้ในโปรแกรม
cv2 (OpenCV) : ใช้สำหรับอ่านและแสดงผลวิดีโอ
ultralytics (YOLO) : ใช้สำหรับตรวจจับวัตถุ
numpy : ใช้ในการคำนวณทางคณิตศาสตร์และเวกเตอร์
requests : ใช้ส่งข้อมูลไปยัง Backend
json : ใช้โหลดและบันทึกค่าการตั้งค่าต่าง ๆ
os : ใช้จัดการกับพาธไฟล์และตัวแปรสภาพแวดล้อม
logging : ใช้จัดการข้อความแจ้งเตือนและข้อผิดพลาด

-----------------------------------------------











