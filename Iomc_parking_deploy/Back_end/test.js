const mysql = require('mysql2');

// Create a connection to MySQL
const connection = mysql.createConnection({
    host: '192.168.100.70',
    user: 'admin',
    password: '1234',
    database: 'smartparking'
});

// Connect to MySQL
connection.connect((err) => {
    if (err) {
        console.error('Error connecting to MySQL:', err);
        return;
    }
    console.log('Connected to MySQL database: smartparking');
    
    // Fetch databases
    connection.query('SHOW DATABASES', (err, results) => {
        if (err) {
            console.error('Error fetching databases:', err);
            return;
        }
        console.log('Databases:', results);
    });

    // Close connection
    connection.end();
});
