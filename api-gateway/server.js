const express = require('express');
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
app.listen(5001, () => console.log('API Gateway running on port 5001'));