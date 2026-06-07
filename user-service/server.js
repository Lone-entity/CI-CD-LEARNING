const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const app = express();
const db = new sqlite3.Database('./users.db');
app.use(express.json());
db.serialize(() => db.run("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, profile_pic TEXT)"));
app.post('/api/users/register', (req, res) => {
    const { username, profile_pic } = req.body;
    db.run("INSERT INTO users (username, profile_pic) VALUES (?, ?)", [username, profile_pic], function(err) {
        if (err) return res.status(500).json({ error: err.message });
        res.json({ id: this.lastID, username });
    });
});
app.listen(5002, () => console.log('User Service running on port 5002'));