require('dotenv').config();
const mysql = require('mysql2');
const express = require('express');
const multer = require('multer');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 4050;

app.use(express.json());

// กำหนดโฟลเดอร์สำหรับเก็บรูป
const uploadDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadDir)) {
    fs.mkdirSync(uploadDir, { recursive: true });
}

// กำหนด multer storage
const storage = multer.diskStorage({
    destination: uploadDir,
    filename: (req, file, cb) => {
        const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
        cb(null, uniqueSuffix + path.extname(file.originalname)); // กำหนดชื่อไฟล์ใหม่
    }
});
const upload = multer({ storage: storage });

// ตั้งค่า MySQL connection
const connection = mysql.createConnection({
    host: process.env.DB_HOST,
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    database: process.env.DB_NAME
});

// API อัปโหลดรูปภาพและบันทึกข้อมูล
app.post("/over_parking", upload.single('image'), (req, res) => {
    console.log("Request Body:", req.body);
    console.log("Uploaded File:", req.file);  // Debugging

    const { roi_id, status, camera_name, location_name, timestamp } = req.body;
    const imagePath = req.file ? `/uploads/${req.file.filename}` : null;

    if (!roi_id || !status || !camera_name || !location_name || !timestamp) {
        return res.status(400).json({ error: "Missing required fields" });
    }

    console.log("Final Image Path:", imagePath);  // Debugging

    const query = `
        INSERT INTO over_parking (roi_id, status, camera_name, location_name, timestamp, image_url)
        VALUES (?, ?, ?, ?, ?, ?)
    `;

    connection.execute(query, [roi_id, status, camera_name, location_name, timestamp, imagePath], (err, results) => {
        if (err) {
            console.error("Error inserting data into MySQL:", err);
            return res.status(500).send("Error inserting data into database");
        }
        res.status(200).json({ message: "Data successfully saved", imageUrl: imagePath });
    });
});

app.use((err, req, res, next) => {
    console.error("Error in Multer:", err);
    res.status(500).json({ error: "File upload failed" });
});


app.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}`);
});
