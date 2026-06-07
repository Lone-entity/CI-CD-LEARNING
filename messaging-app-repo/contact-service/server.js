const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const app = express();
const db = new sqlite3.Database('./contacts.db');
app.use(express.json());
db.serialize(() => {
    db.run("CREATE TABLE IF NOT EXISTS contacts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, contact_id INTEGER)");
    db.run("CREATE TABLE IF NOT EXISTS status (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, text TEXT)");
});
app.post('/api/contacts/status', (req, res) => {
    db.run("INSERT INTO status (user_id, text) VALUES (?, ?)", [req.body.user_id, req.body.text], function(err) {
        if (err) return res.status(500).json({ error: err.message });
        res.json({ success: true, status_id: this.lastID });
    });
});
app.listen(5003, () => console.log('Contact Service running on port 5003'));