const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');
require('dotenv').config();

// Configuration
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000/api/v1/ingest';
const API_KEY = process.env.API_KEY;

if (!API_KEY) {
    throw new Error('API_KEY environment variable is not set');
}

const ALLOWED_GROUPS = process.env.ALLOWED_GROUPS ? process.env.ALLOWED_GROUPS.split(',') : [];

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
        const chat = await msg.getChat();

        // Only monitor group chats
        if (!chat.isGroup) return;

        // Filter by allowed groups if configured
        if (ALLOWED_GROUPS.length > 0 && !ALLOWED_GROUPS.includes(chat.id._serialized)) {
            return;
        }

        const contact = await msg.getContact();
        
        // Construct the payload for the AI backend
        const payload = {
            message_id: msg.id._serialized,
            group_id: chat.id._serialized,
            group_name: chat.name,
            sender_id: contact.id._serialized,
            sender_name: contact.pushname || contact.name || 'Unknown',
            content: msg.body,
            timestamp: msg.timestamp,
            is_media: msg.hasMedia,
            quoted_msg_id: msg.hasQuotedMsg ? (await msg.getQuotedMessage()).id._serialized : null,
        };

        // Forward to backend asynchronously
        forwardToBackend(payload);
        
    } catch (error) {
        console.error('⚠️ Error processing message:', error.message);
    }
});

async function forwardToBackend(payload) {
    try {
        await axios.post(BACKEND_URL, payload, {
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': API_KEY
            },
            timeout: 5000 // 5 second timeout so we don't block
        });
        console.log(`[SENT] ${payload.group_name} | ${payload.sender_name}: ${payload.content.substring(0, 30)}...`);
    } catch (error) {
        console.error(`[FAILED] Sending to backend: ${error.message}`);
        // Note: A production system would push this to a Redis retry queue here.
    }
}

// Start the client
client.initialize();
