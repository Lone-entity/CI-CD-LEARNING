import os

base_dir = "messaging-app-repo"

# File contents
files = {
    ".github/workflows/ci.yml": """name: Microservices CI
on:
  push:
    branches: [ main ]
jobs:
  build-and-push:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [api-gateway, user-service, contact-service, chat-service, group-service, notification-service, analytics-service, frontend]
    steps:
      - uses: actions/checkout@v3
      - uses: docker/setup-buildx-action@v2
      - uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v4
        with:
          context: ./${{ matrix.service }}
          file: ./${{ matrix.service }}/Dockerfile
          push: true
          tags: ghcr.io/${{ github.repository }}/${{ matrix.service }}:latest""",

    "frontend/index.html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Messaging App</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 h-screen flex">
    <div class="w-1/3 bg-white border-r flex flex-col">
        <div class="bg-gray-200 h-16 flex items-center px-4 font-bold text-gray-700">Contacts & Groups</div>
        <div class="p-2 border-b"><input type="text" placeholder="Search contacts" class="w-full p-2 rounded bg-gray-100 outline-none"></div>
        <div class="flex-1 overflow-y-auto" id="contact-list">
            <div class="p-4 border-b hover:bg-gray-50 cursor-pointer">
                <div class="font-semibold">General Chat</div>
                <div class="text-sm text-gray-500">Latest status update</div>
            </div>
        </div>
    </div>
    <div class="flex-1 flex flex-col bg-slate-50">
        <div class="bg-gray-200 h-16 flex items-center px-4 font-bold text-gray-700">Active Chat</div>
        <div class="flex-1 p-4 overflow-y-auto flex flex-col space-y-4" id="chat-window">
            <div class="bg-white p-3 rounded-lg shadow-sm self-start max-w-md">Hello there</div>
        </div>
        <div class="bg-gray-200 p-4 flex items-center">
            <input type="text" id="message-input" placeholder="Type a message" class="flex-1 p-2 rounded outline-none mr-2">
            <button onclick="sendMessage()" class="bg-green-500 text-white px-4 py-2 rounded">Send</button>
        </div>
    </div>
    <script>
        async function sendMessage() {
            const input = document.getElementById('message-input');
            const text = input.value;
            if (!text) return;
            document.getElementById('chat-window').innerHTML += `<div class="bg-green-100 p-3 rounded-lg shadow-sm self-end max-w-md">${text}</div>`;
            input.value = '';
            try {
                await fetch('http://localhost:5001/api/chat/send', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ senderId: 1, receiverId: 2, content: text })
                });
            } catch (e) { console.error(e); }
        }
    </script>
</body>
</html>""",

    "frontend/server.js": """const express = require('express');\nconst path = require('path');\nconst app = express();\napp.use(express.static(__dirname));\napp.get('*', (req, res) => res.sendFile(path.join(__dirname, 'index.html')));\napp.listen(5000, () => console.log('Frontend serving on port 5000'));""",

    "api-gateway/server.js": """const express = require('express');
const cors = require('cors');
const app = express();
app.use(cors());
app.use(express.json());

const routes = {
    '/api/users': 'http://user-service:5002',
    '/api/contacts': 'http://contact-service:5003',
    '/api/chat': 'http://chat-service:5004',
    '/api/groups': 'http://group-service:5005'
};

app.use(async (req, res) => {
    const targetBase = Object.keys(routes).find(route => req.path.startsWith(route));
    if (!targetBase) return res.status(404).send('Service not found');
    try {
        const fetch = (await import('node-fetch')).default;
        const response = await fetch(routes[targetBase] + req.path, {
            method: req.method, headers: { 'Content-Type': 'application/json' },
            body: ['POST', 'PUT'].includes(req.method) ? JSON.stringify(req.body) : undefined
        });
        res.status(response.status).json(await response.json());
    } catch (e) { res.status(500).json({ error: 'Gateway routing failed' }); }
});
app.listen(5001, () => console.log('API Gateway running on port 5001'));""",

    "user-service/server.js": """const express = require('express');
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
app.listen(5002, () => console.log('User Service running on port 5002'));""",

    "contact-service/server.js": """const express = require('express');
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
app.listen(5003, () => console.log('Contact Service running on port 5003'));""",

    "chat-service/server.js": """const express = require('express');
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
app.listen(5004, () => console.log('Chat Service running on port 5004'));""",

    "group-service/server.js": """const express = require('express');
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
app.listen(5005, () => console.log('Group Service running on port 5005'));""",

    "notification-service/server.js": """const { Kafka } = require('kafkajs');
const kafka = new Kafka({ clientId: 'notification-service', brokers: ['kafka-service:9092'] });
const consumer = kafka.consumer({ groupId: 'notification-group' });
async function start() {
    try {
        await consumer.connect();
        await consumer.subscribe({ topic: 'unprocessed-message', fromBeginning: true });
        await consumer.run({ eachMessage: async ({ message }) => console.log(`Notification for message ${JSON.parse(message.value.toString()).messageId}`) });
    } catch(e) { setTimeout(start, 5000); }
}
start();""",

    "analytics-service/server.js": """const sqlite3 = require('sqlite3').verbose();
const { Kafka } = require('kafkajs');
const db = new sqlite3.Database('./audit.db');
const kafka = new Kafka({ clientId: 'analytics-service', brokers: ['kafka-service:9092'] });
const consumer = kafka.consumer({ groupId: 'analytics-group' });
db.serialize(() => db.run("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT, payload TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)"));
async function start() {
    try {
        await consumer.connect();
        await consumer.subscribe({ topic: 'unprocessed-message', fromBeginning: true });
        await consumer.run({ eachMessage: async ({ message }) => db.run("INSERT INTO events (event_type, payload) VALUES (?, ?)", ['message_sent', message.value.toString()]) });
    } catch(e) { setTimeout(start, 5000); }
}
start();""",

    "k8s/argo-application.yaml": """apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: messaging-ecosystem
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/messaging-platform.git
    targetRevision: HEAD
    path: k8s/messaging-chart
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated: { prune: true, selfHeal: true }""",

    "k8s/messaging-chart/Chart.yaml": "apiVersion: v2\nname: messaging-chart\nversion: 0.1.0",
    
    "k8s/messaging-chart/values.yaml": """services:
  - {name: frontend, port: 5000}
  - {name: api-gateway, port: 5001}
  - {name: user-service, port: 5002}
  - {name: contact-service, port: 5003}
  - {name: chat-service, port: 5004}
  - {name: group-service, port: 5005}
  - {name: notification-service, port: 5006}
  - {name: analytics-service, port: 5007}
resources:
  requests: {cpu: 50m}
  limits: {cpu: 100m}""",

    "k8s/messaging-chart/templates/deployment-template.yaml": """{{- range .Values.services }}
apiVersion: apps/v1
kind: Deployment
metadata: { name: {{ .name }} }
spec:
  replicas: 1
  selector: { matchLabels: { app: {{ .name }} } }
  template:
    metadata: { labels: { app: {{ .name }} } }
    spec:
      containers:
        - name: {{ .name }}
          image: ghcr.io/your-org/{{ .name }}:latest
          ports: [ { containerPort: {{ .port }} } ]
---
apiVersion: v1
kind: Service
metadata: { name: {{ .name }} }
spec:
  selector: { app: {{ .name }} }
  ports: [ { protocol: TCP, port: {{ .port }}, targetPort: {{ .port }} } ]
---
{{- end }}""",

    "k8s/messaging-chart/templates/cilium-network-policy.yaml": """apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata: { name: api-gateway-policy }
spec:
  endpointSelector: { matchLabels: { app: api-gateway } }
  ingress: [ { toPorts: [ { ports: [ { port: "5001", protocol: TCP } ], rules: { http: [ {} ] } } ] } ]""",

    "README.md": "# Messaging App\nRun `npm install` and `npm start` in each module."
}

# Add Dockerfile and package.json for all services
services = ["frontend", "api-gateway", "user-service", "contact-service", "chat-service", "group-service", "notification-service", "analytics-service"]
dockerfile_content = "FROM node:18-alpine\nWORKDIR /app\nCOPY package*.json ./\nRUN npm install\nCOPY . .\nEXPOSE 5000-5010\nCMD [\"node\", \"server.js\"]"

for svc in services:
    files[f"{svc}/Dockerfile"] = dockerfile_content
    files[f"{svc}/package.json"] = f'{{\n  "name": "{svc}",\n  "version": "1.0.0",\n  "main": "server.js",\n  "scripts": {{ "start": "node server.js" }},\n  "dependencies": {{ "express": "^4.18.2", "sqlite3": "^5.1.6", "cors": "^2.8.5", "kafkajs": "^2.2.4", "node-fetch": "^3.3.2" }}\n}}'

# Create files and directories
print(f"Building project in ./{base_dir} ...")
for file_path, content in files.items():
    full_path = os.path.join(base_dir, file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip())

print("✅ Success! All folders and files have been created.")