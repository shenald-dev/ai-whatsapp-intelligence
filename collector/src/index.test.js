const test = require('node:test');
const assert = require('node:assert');
const { handleMessage } = require('./index');

test('handleMessage safely handles missing properties and quoted messages', async () => {
    // Create a mock payload to capture the forwarded data
    let capturedPayload = null;

    // We override forwardToBackend for the test scope if possible
    // Since handleMessage calls it directly, we can mock console.log and axios or just test handleMessage safely.
    // Instead of mocking the module export directly which is tricky in CommonJS without proxyquire,
    // let's test handleMessage and observe it does not throw when properties are missing.

    // We can intercept the call to forwardToBackend by temporarily overriding the global axios object
    // or by checking that no exceptions are thrown and relying on the payload structure logic.
    // However, handleMessage calls forwardToBackend directly, which might make a network request.
    // So let's mock axios to intercept the payload and avoid actual network calls.
    const axios = require('axios');
    const originalPost = axios.post;
    axios.post = async (url, payload, config) => {
        capturedPayload = payload;
        return { status: 200 };
    };

    // Create a mock message with deep missing properties
    const mockMsg = {
        id: { _serialized: 'msg-123' },
        body: 'Hello test',
        timestamp: 1234567890,
        hasMedia: false,
        hasQuotedMsg: true,
        getChat: async () => ({
            isGroup: true,
            id: { _serialized: 'group-123' },
            name: 'Test Group'
        }),
        getContact: async () => ({
            id: { _serialized: 'user-123' },
            pushname: 'Test User'
        }),
        // Crucial test: getQuotedMessage returns an object missing the expected .id._serialized path
        getQuotedMessage: async () => ({
            // Intentionally omit id._serialized to test optional chaining
            id: null
        })
    };

    // Replace original console.error to avoid test noise
    const originalConsoleError = console.error;
    let loggedError = null;
    console.error = (msg, err) => {
        loggedError = err;
    };

    try {
        await handleMessage(mockMsg);

        // Verify the function handled the missing quoted msg id gracefully
        assert.strictEqual(loggedError, null, 'handleMessage should not throw any errors');

        assert.ok(capturedPayload, 'forwardToBackend should have been called with a payload');
        assert.strictEqual(capturedPayload.message_id, 'msg-123');
        assert.strictEqual(capturedPayload.group_id, 'group-123');
        assert.strictEqual(capturedPayload.sender_id, 'user-123');
        assert.strictEqual(capturedPayload.quoted_msg_id, null, 'quoted_msg_id should safely resolve to null when missing');

    } finally {
        // Restore mocks
        axios.post = originalPost;
        console.error = originalConsoleError;
    }
});
