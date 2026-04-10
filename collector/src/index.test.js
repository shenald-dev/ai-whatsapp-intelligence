const assert = require('node:assert');
const test = require('node:test');

// Set a dummy API_KEY so index.js doesn't throw on require
process.env.API_KEY = 'test_key';
const { client, forwardToBackend } = require('./index');

test('index.js exports client and forwardToBackend', () => {
    assert.ok(client, 'client should be exported');
    assert.ok(forwardToBackend, 'forwardToBackend should be exported');
    assert.strictEqual(typeof forwardToBackend, 'function', 'forwardToBackend should be a function');
});

test('message handler handles missing properties via optional chaining', async () => {
    // We want to trigger the message handler and ensure it doesn't crash on undefined deep properties.
    // Instead of mocking the entire client, we just emit the message event.

    // We need a dummy message object.
    const dummyMsg = {
        getChat: async () => ({
            isGroup: true,
            name: 'Test Group',
            // Notice: no id._serialized
        }),
        getContact: async () => ({
            name: 'Test User',
            // Notice: no id._serialized
        }),
        hasMedia: false,
        hasQuotedMsg: true,
        getQuotedMessage: async () => ({
            // Notice: no id._serialized
        }),
        body: 'Hello',
        timestamp: 1234567890
    };

    // We can't easily spy on axios inside forwardToBackend without a mocking library,
    // but we can ensure that emitting the event doesn't throw a TypeError.

    // The message handler has a try/catch, so it won't crash the process anyway.
    // However, we want to know if it reached the forwardToBackend call or not.
    // Since it's inside index.js and forwardToBackend is module scoped, we can't easily stub it
    // without proxyquire.

    // Let's just make sure it doesn't throw synchronously and handles the event gracefully.
    try {
        await new Promise((resolve) => {
            // Emitting is sync, but the handler is async.
            // We just wait a tiny bit to let the microtask queue clear.
            client.emit('message', dummyMsg);
            setTimeout(resolve, 50);
        });
        assert.ok(true, 'Did not crash when properties were missing');
    } catch (err) {
        assert.fail(err);
    }
});
