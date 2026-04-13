const test = require('node:test');
const assert = require('node:assert');
const { forwardToBackend } = require('../src/index.js');
const axios = require('axios');

test('forwardToBackend calls axios.post with correct payload and headers', async (t) => {
    // Mock axios.post
    let postCalled = false;
    let postedUrl;
    let postedPayload;
    let postedHeaders;

    const originalPost = axios.post;
    axios.post = async (url, payload, options) => {
        postCalled = true;
        postedUrl = url;
        postedPayload = payload;
        postedHeaders = options.headers;
        return { status: 200 };
    };

    try {
        const mockPayload = {
            message_id: 'test_msg_id',
            group_id: 'test_group_id',
            group_name: 'Test Group',
            sender_id: 'test_sender_id',
            sender_name: 'Test Sender',
            content: 'Test content',
            timestamp: 1234567890,
            is_media: false,
            quoted_msg_id: null
        };

        // Override console.log to suppress expected output during test
        const originalConsoleLog = console.log;
        console.log = () => {};

        await forwardToBackend(mockPayload);

        console.log = originalConsoleLog;

        assert.strictEqual(postCalled, true, 'axios.post should be called');
        assert.strictEqual(postedUrl, process.env.BACKEND_URL || 'http://localhost:8000/api/v1/ingest', 'Should post to correct URL');
        assert.deepStrictEqual(postedPayload, mockPayload, 'Should post the correct payload');
        assert.strictEqual(postedHeaders['Content-Type'], 'application/json', 'Should have correct Content-Type header');
        assert.strictEqual(postedHeaders['X-API-Key'], process.env.API_KEY, 'Should have correct X-API-Key header');

    } finally {
        // Restore original axios.post
        axios.post = originalPost;
    }
});
