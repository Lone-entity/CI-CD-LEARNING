const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const { Kafka } = require('kafkajs');
const app = express();
const db = new sqlite3.Database('./chats.db');
app.use(express.json());
const kafka = new Kafka({ clientId: 'chat-service', brokers: ['kafka-service:9092'] });
const producer = kafka.producer();
db.serialize(() => db.run("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER, receiver_id INTEGER, content TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)"));

app.post('/api/chat/send', async (req, res) => {
    const { senderId, receiverId, content } = req.body;
    try { await producer.connect(); } catch (e) { console.log("Kafka not ready"); }
    db.run("INSERT INTO messages (sender_id, receiver_id, content) VALUES (?, ?, ?)", [senderId, receiverId, content], async function(err) {
        if (err) return res.status(500).json({ error: err.message });
        try { await producer.send({ topic: 'unprocessed-message', messages: [{ value: JSON.stringify({ messageId: this.lastID, senderId, receiverId, content }) }] }); } catch(e) {}
        res.json({ success: true, messageId: this.lastID });
    });
});
app.listen(5004, () => console.log('Chat Service running on port 5004'));