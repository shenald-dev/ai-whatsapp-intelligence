const test = require('node:test');
const assert = require('node:assert');
const { processMessage } = require('../src/index.js');

test('processMessage handles malformed objects safely without crashing', async () => {
    let forwardCalled = false;
    let forwardedPayload = null;

    // Mock module.exports.forwardToBackend
    const originalForward = require('../src/index.js').forwardToBackend;
    require('../src/index.js').forwardToBackend = (payload) => {
        forwardCalled = true;
        forwardedPayload = payload;
    };

    // Construct a mock message with missing properties
    const mockMsg = {
        getChat: async () => ({
            isGroup: true,
            // Missing id._serialized and name
        }),
        getContact: async () => ({
            // Missing id._serialized, pushname, name
        }),
        // Missing id._serialized, body, timestamp, hasMedia, hasQuotedMsg
    };

    // This should not throw due to optional chaining
    await assert.doesNotReject(async () => {
        await processMessage(mockMsg);
    });

    assert.strictEqual(forwardCalled, true, 'forwardToBackend should be called');

    // Verify that missing fields resulted in undefined/null in payload
    assert.strictEqual(forwardedPayload.message_id, undefined);
    assert.strictEqual(forwardedPayload.group_id, undefined);
    assert.strictEqual(forwardedPayload.group_name, undefined);
    assert.strictEqual(forwardedPayload.sender_id, undefined);
    assert.strictEqual(forwardedPayload.sender_name, 'Unknown');
    assert.strictEqual(forwardedPayload.content, undefined);
    assert.strictEqual(forwardedPayload.timestamp, undefined);
    assert.strictEqual(forwardedPayload.is_media, undefined);
    assert.strictEqual(forwardedPayload.quoted_msg_id, null);

    // Restore original forward function
    require('../src/index.js').forwardToBackend = originalForward;
});

test('processMessage properly extracts fields from well-formed objects', async () => {
    let forwardCalled = false;
    let forwardedPayload = null;

    // Mock module.exports.forwardToBackend
    const originalForward = require('../src/index.js').forwardToBackend;
    require('../src/index.js').forwardToBackend = (payload) => {
        forwardCalled = true;
        forwardedPayload = payload;
    };

    const mockMsg = {
        id: { _serialized: 'msg_123' },
        body: 'Hello World',
        timestamp: 1234567890,
        hasMedia: false,
        hasQuotedMsg: true,
        getChat: async () => ({
            isGroup: true,
            id: { _serialized: 'group_123' },
            name: 'Test Group'
        }),
        getContact: async () => ({
            id: { _serialized: 'contact_123' },
            pushname: 'Alice',
            name: 'Alice Smith'
        }),
        getQuotedMessage: async () => ({
            id: { _serialized: 'quoted_123' }
        })
    };

    await assert.doesNotReject(async () => {
        await processMessage(mockMsg);
    });

    assert.strictEqual(forwardCalled, true);
    assert.strictEqual(forwardedPayload.message_id, 'msg_123');
    assert.strictEqual(forwardedPayload.group_id, 'group_123');
    assert.strictEqual(forwardedPayload.group_name, 'Test Group');
    assert.strictEqual(forwardedPayload.sender_id, 'contact_123');
    assert.strictEqual(forwardedPayload.sender_name, 'Alice');
    assert.strictEqual(forwardedPayload.content, 'Hello World');
    assert.strictEqual(forwardedPayload.timestamp, 1234567890);
    assert.strictEqual(forwardedPayload.is_media, false);
    assert.strictEqual(forwardedPayload.quoted_msg_id, 'quoted_123');

    // Restore original forward function
    require('../src/index.js').forwardToBackend = originalForward;
});
