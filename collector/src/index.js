const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');
const http = require('http');
const https = require('https');
require('dotenv').config();

// Configuration
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000/api/v1/ingest';
const API_KEY = process.env.API_KEY;

if (!API_KEY) {
    throw new Error('API_KEY environment variable is not set');
}

function parseAllowedGroups(envStr) {
    if (!envStr) return new Set();
    return new Set(envStr.split(',').map(s => s.trim()).filter(Boolean));
}

const ALLOWED_GROUPS = parseAllowedGroups(process.env.ALLOWED_GROUPS);
const MAX_CONCURRENT_REQUESTS = parseInt(process.env.MAX_CONCURRENT_REQUESTS || '100', 10);

console.log('🚀 AI WhatsApp Intelligence Collector Starting...');
console.log(`📡 Backend URL: ${BACKEND_URL}`);

// Initialize client with safe session storage
const client = new Client({
    authStrategy: new LocalAuth({ dataPath: './.wwebjs_auth' }),
    puppeteer: {
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

client.on('qr', (qr) => {
    console.log('\n📱 Scan this QR code with WhatsApp to log in:');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('\n✅ Client is ready! Monitoring groups...');
});

client.on('authenticated', () => {
    console.log('🔒 Authenticated successfully.');
});

client.on('auth_failure', msg => {
    console.error('❌ Authentication failure', msg);
});

// Primary Message Listener
client.on('message', async (msg) => {
    try {
        // Fast-path early returns to avoid expensive await msg.getChat()
        if (!msg.from?.endsWith('@g.us')) return;
        if (ALLOWED_GROUPS.size > 0 && !ALLOWED_GROUPS.has(msg.from)) return;

        // Parallelize expensive asynchronous operations with error handling
        const [chat, contact, quotedMsg] = await Promise.all([
            msg.getChat().catch(e => {
                console.error(`⚠️ Failed to fetch chat for ${msg.id._serialized}:`, e.message);
                return null;
            }),
            msg.getContact().catch(e => {
                console.error(`⚠️ Failed to fetch contact for ${msg.id._serialized}:`, e.message);
                return null;
            }),
            (msg.hasQuotedMsg ? msg.getQuotedMessage() : Promise.resolve(null)).catch(e => {
                console.error(`⚠️ Failed to fetch quoted msg for ${msg.id._serialized}:`, e.message);
                return null;
            })
        ]);
        
        // Ensure we have the minimum required entities
        if (!chat || !contact) return;

        // Construct the payload for the AI backend
        const payload = {
            message_id: (msg.id._serialized || '').substring(0, 255),
            group_id: (chat.id._serialized || '').substring(0, 255),
            group_name: (chat.name || '').substring(0, 255),
            sender_id: (contact.id._serialized || '').substring(0, 255),
            sender_name: (contact.pushname || contact.name || 'Unknown').substring(0, 255),
            content: (msg.body || '').substring(0, 65536),
            timestamp: msg.timestamp,
            is_media: msg.hasMedia,
            quoted_msg_id: quotedMsg?.id?._serialized ? quotedMsg.id._serialized.substring(0, 255) : null,
        };

        // Forward to backend asynchronously
        forwardToBackend(payload);
        
    } catch (error) {
        console.error('⚠️ Error processing message:', error.message);
    }
});

// Configure axios instance with keepAlive and concurrency limit to reuse TCP connections
const apiClient = axios.create({
    httpAgent: new http.Agent({ keepAlive: true, maxSockets: MAX_CONCURRENT_REQUESTS }),
    httpsAgent: new https.Agent({ keepAlive: true, maxSockets: MAX_CONCURRENT_REQUESTS }),
    headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY
    },
    timeout: 5000 // 5 second timeout so we don't block
});

async function forwardToBackend(payload) {
    try {
        await apiClient.post(BACKEND_URL, payload);
        console.log(`[SENT] ${payload.group_name} | ${payload.sender_name}: ${payload.content.substring(0, 30)}...`);
    } catch (error) {
        console.error(`[FAILED] Sending to backend: ${error.message}`);
        // Note: A production system would push this to a Redis retry queue here.
    }
}

// Start the client only if run directly
if (require.main === module) {
    client.initialize();
}

module.exports = {
    parseAllowedGroups,
    forwardToBackend,
    client // export for testing if needed
};
