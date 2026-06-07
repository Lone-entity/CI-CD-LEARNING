const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const app = express();
const db = new sqlite3.Database('./groups.db');
app.use(express.json());
db.serialize(() => {
    db.run("CREATE TABLE IF NOT EXISTS groups (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, admin_id INTEGER)");
    db.run("CREATE TABLE IF NOT EXISTS members (group_id INTEGER, user_id INTEGER)");
});
app.post('/api/groups/create', (req, res) => {
    db.run("INSERT INTO groups (name, admin_id) VALUES (?, ?)", [req.body.name, req.body.admin_id], function(err) {
        if (err) return res.status(500).json({ error: err.message });
        res.json({ success: true, group_id: this.lastID });
    });
});
app.listen(5005, () => console.log('Group Service running on port 5005'));