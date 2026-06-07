const sqlite3 = require("sqlite3").verbose();
const { Kafka } = require("kafkajs");
const db = new sqlite3.Database("./audit.db");
const kafka = new Kafka({
  clientId: "analytics-service",
  brokers: ["kafka-service:9092"],
});
const consumer = kafka.consumer({ groupId: "analytics-group" });
db.serialize(() =>
  db.run(
    "CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT, payload TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)",
  ),
);
async function start() {
  try {
    console.log("Starting analytics service...");
    await consumer.connect();
    await consumer.subscribe({
      topic: "unprocessed-message",
      fromBeginning: true,
    });
    await consumer.run({
      eachMessage: async ({ message }) =>
        db.run("INSERT INTO events (event_type, payload) VALUES (?, ?)", [
          "message_sent",
          message.value.toString(),
        ]),
    });
  } catch (e) {
    setTimeout(start, 5000);
  }
}
start();
