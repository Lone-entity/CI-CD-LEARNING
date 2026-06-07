const { Kafka } = require('kafkajs');
const kafka = new Kafka({ clientId: 'notification-service', brokers: ['kafka-service:9092'] });
const consumer = kafka.consumer({ groupId: 'notification-group' });
async function start() {
    try {
        await consumer.connect();
        await consumer.subscribe({ topic: 'unprocessed-message', fromBeginning: true });
        await consumer.run({ eachMessage: async ({ message }) => console.log(`Notification for message ${JSON.parse(message.value.toString()).messageId}`) });
    } catch(e) { setTimeout(start, 5000); }
}
start();