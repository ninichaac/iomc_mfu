require('dotenv').config();

const mysql = require('mysql2');
const express = require('express');
const { now } = require('sequelize/lib/utils');
const app = express();
const port = 3050;


// SQL connection
const connection = mysql.createConnection({
    host: process.env.DB_HOST,
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    database: process.env.DB_NAME
});

// Global variables
let lkb_out_001 = 4;
let Total_cars = 0;
let previousCount = 0;
let areaZones = [];

// API to get Car Count
app.get('/Car_count', (req, res) => {
    const carCount = req.body.car_out;
    const areaZone = req.body.area_zone;
    console.log(`Total Cars: ${Total_cars} : ${areaZones}`);
    res.status(200).send(`${carCount} : ${areaZone}`);
});

// API to post Car Count and Area Zone
app.post('/Car_count', express.json(), (req, res) => {
    const carCount = req.body.car_out;
    const areaZone = req.body.area_zone;

    if (carCount != null && !isNaN(carCount) && areaZone) {
        Total_cars = carCount;

        if (!areaZones.includes(areaZone)) {
            areaZones.push(areaZone); // Add unique area zones
        }

        console.log(`Updated Total Cars: ${Total_cars}, Area Zones: ${areaZones}`);
        res.status(200).send("Car count updated successfully");
    } else {
        res.status(400).send("Invalid data: Ensure 'car_out' and 'area_zone' are provided correctly.");
    }
});

// Function to upload Car Count
const uploadCarCount = (areaZone,formattedDate) => {
    if (!areaZone) {
        console.error("Error: areaZone is required for uploading car count.");
        return;
    }

    const newCarCount = Math.max(Total_cars - previousCount, 0); // Calculate the new car count
    const query = 'INSERT INTO counting_car (area_zone, timestamp, quantity, total ,Vehicletype) VALUES (?, ?, ?, ? ,1)';
    const time = formattedDate; // Get current time
    connection.query(query, [areaZone, time, newCarCount, Total_cars, 1], (err) => {
        if (err) {
            console.error("Error uploading car count with area zone:", err);
            return;
        }
        console.log(`Uploaded ${newCarCount} for area zone: ${areaZone} to SQL.`);
        previousCount = Total_cars; // Update the previous count
    });
};


// Set interval to upload car count every 1 minute
setInterval(() => {
    const now = new Date();
    const formattedDate = formatDate(now);
    if (now.getSeconds() === 0) {
        if (areaZones.length === 0) {
            console.error("Error: No `areaZone` values available.");
            return;
        }

        areaZones.forEach((zone) => {
            uploadCarCount(zone,formattedDate);
        });
    }
}, 1000);

function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0'); // เดือนเริ่มจาก 0 ต้อง +1
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');

    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}


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
