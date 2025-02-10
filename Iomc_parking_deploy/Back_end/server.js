require('dotenv').config();

const mysql = require('mysql2');
const express = require('express');
const { now } = require('sequelize/lib/utils');
const app = express();
const port = 3001;

app.use(express.json());
// SQL connection
const connection = mysql.createConnection({
    host: process.env.DB_HOST,
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    database: process.env.DB_NAME
});

// Global variables
let lkb_out_001 = 10;


// API to get Car Count



app.put("/update-area-zone", (req, res) => {
    const { area_zone, total } = req.body;
    if (!area_zone || typeof total === "undefined") {
      return res.status(400).json({ error: "กรุณาระบุ area และ จำนวนรถ" });
    }
  
    // คำนวณ totalupdate
     // ตัวอย่างค่า lkb_out_001
    let totalupdate = lkb_out_001 - total;
    if (totalupdate < 0) {
      totalupdate = 0;
    }
  
    // สร้างคำสั่ง SQL สำหรับอัปเดตข้อมูล
    const sql = "UPDATE car_parking_space SET free_space = ? WHERE area_zone = ?";
    connection.query(sql, [totalupdate, area_zone], (err, result) => {
      if (err) {
        console.error("เกิดข้อผิดพลาดในการอัปเดตข้อมูล: ", err);
        return res.status(500).json({ error: "เกิดข้อผิดพลาดในการอัปเดตข้อมูล" });
      }
  
      if (result.affectedRows === 0) {
        return res.status(404).json({ message: "ไม่พบ area ที่มีชื่อนี้" });
      }
  
      res.status(200).json({ message: "อัปเดตข้อมูลสำเร็จ!" });
    });
  });



// Log connection status
connection.connect((err) => {
    if (err) {
        console.error('Error connecting to the database:', err.message);
        return;
    }
    console.log('Connected to the database.');
});

// Start the server
app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});
