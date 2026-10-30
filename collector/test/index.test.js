const { test } = require('node:test');
const assert = require('node:assert');
const proxyquire = require('proxyquire');

// Mock axios so we don't make real network calls
let axiosPostCalledWith = null;
const axiosMock = {
    create: (config) => {
        // Return a mock instance that captures the config passed to create
        return {
            defaults: config,
            post: async (url, payload, reqConfig) => {
                axiosPostCalledWith = { url, payload, config: { ...config, ...reqConfig } };
                return { status: 200 };
            }
        };
    }
};

// We need to inject the environment variable BEFORE requiring the script
process.env.API_KEY = 'test_key';

let messageHandler = null;

const { parseAllowedGroups, safeTruncate, forwardToBackend } = proxyquire('../src/index.js', {
    'axios': axiosMock,
    'whatsapp-web.js': {
        Client: class {
            on(event, handler) {
                if (event === 'message') {
                    messageHandler = handler;
                }
            }
            initialize() {}
        },
        LocalAuth: class {}
    },
    'qrcode-terminal': {
        generate: () => {}
    }
});

test('parseAllowedGroups correctly parses comma separated string into a Set', () => {
    const result = parseAllowedGroups('group1,group2, group3 ');
    assert.ok(result instanceof Set);
    assert.strictEqual(result.size, 3);
    assert.ok(result.has('group1'));
    assert.ok(result.has('group2'));
    assert.ok(result.has('group3'));
});

test('parseAllowedGroups handles empty or null input', () => {
    assert.strictEqual(parseAllowedGroups('').size, 0);
    assert.strictEqual(parseAllowedGroups(null).size, 0);
    assert.strictEqual(parseAllowedGroups(undefined).size, 0);
});

test('safeTruncate handles edge cases gracefully', () => {
    assert.strictEqual(safeTruncate(null, 10, 'field'), '');
    assert.strictEqual(safeTruncate(undefined, 10, 'field'), '');
    assert.strictEqual(safeTruncate('hello', 10, 'field'), 'hello');
    assert.strictEqual(safeTruncate('hello world', 5, 'field'), 'hello');
});

test('forwardToBackend calls axios with correct payload and headers', async () => {
    const payload = {
        group_name: 'Test Group',
        sender_name: 'Alice',
        content: 'Hello World'
    };

    // Reset our mock state
    axiosPostCalledWith = null;

    await forwardToBackend(payload);

    assert.ok(axiosPostCalledWith !== null, 'axios.post was not called');
    assert.strictEqual(axiosPostCalledWith.payload, payload);
    assert.strictEqual(axiosPostCalledWith.config.headers['X-API-Key'], 'test_key');
});

test('message handler truncates long strings to avoid 422 Unprocessable Entity', async () => {
    // Reset our mock state
    axiosPostCalledWith = null;

    // Save old console.warn to check for the warning and prevent output spam
    const originalWarn = console.warn;
    let warningLogged = false;
    console.warn = (msg) => {
        if (msg.includes('Warning: Truncating')) {
            warningLogged = true;
        }
    };

    // Construct mock objects that return excessively long strings
    const longString260 = 'a'.repeat(260);
    const longString70000 = 'b'.repeat(70000);

    const mockMsg = {
        id: { _serialized: longString260 },
        from: '12345@g.us', // Pass the allowed groups check
        body: longString70000,
        timestamp: 1234567890,
        hasMedia: false,
        hasQuotedMsg: true,
        getChat: async () => ({ id: { _serialized: longString260 }, name: longString260 }),
        getContact: async () => ({ id: { _serialized: longString260 }, pushname: longString260 }),
        getQuotedMessage: async () => ({ id: { _serialized: longString260 } })
    };

    await messageHandler(mockMsg);

    // Restore original console.warn
    console.warn = originalWarn;

    assert.ok(axiosPostCalledWith !== null, 'axios.post was not called');
    const sentPayload = axiosPostCalledWith.payload;

    assert.strictEqual(sentPayload.message_id.length, 255);
    assert.strictEqual(sentPayload.group_id.length, 255);
    assert.strictEqual(sentPayload.group_name.length, 255);
    assert.strictEqual(sentPayload.sender_id.length, 255);
    assert.strictEqual(sentPayload.sender_name.length, 255);
    assert.strictEqual(sentPayload.content.length, 65536);
    assert.strictEqual(sentPayload.quoted_msg_id.length, 255);

    assert.ok(warningLogged, 'Expected a truncation warning to be logged');
});

test('message handler safely ignores messages missing essential ID structures', async () => {
    axiosPostCalledWith = null;

    // Missing id object
    const brokenMsg = {
        from: 'group123@g.us',
        getChat: async () => ({ id: { _serialized: 'grp1' } }),
        getContact: async () => ({ id: { _serialized: 'usr1' } })
    };
    await messageHandler(brokenMsg);
    assert.strictEqual(axiosPostCalledWith, null, 'Should not forward message without id');

    // Missing chat id
    const brokenChatMsg = {
        id: { _serialized: 'msg1' },
        from: 'group123@g.us',
        getChat: async () => ({ name: 'Group' }),
        getContact: async () => ({ id: { _serialized: 'usr1' } })
    };
    await messageHandler(brokenChatMsg);
    assert.strictEqual(axiosPostCalledWith, null, 'Should not forward message without chat id');
});

test('message handler sanitizes timestamp and boolean media flag', async () => {
    axiosPostCalledWith = null;

    const validMsg = {
        id: { _serialized: 'msg_ts_test' },
        from: 'group123@g.us',
        body: 'Testing timestamp sanitization',
        timestamp: 'invalid_string',
        hasMedia: undefined,
        hasQuotedMsg: false,
        getChat: async () => ({ id: { _serialized: 'grp_ts' }, name: 'TS Group' }),
        getContact: async () => ({ id: { _serialized: 'usr_ts' }, pushname: 'TS User' })
    };

    const before = Math.floor(Date.now() / 1000);
    await messageHandler(validMsg);
    const after = Math.floor(Date.now() / 1000);

    assert.ok(axiosPostCalledWith !== null, 'axios.post should have been called');
    const payload = axiosPostCalledWith.payload;
    assert.strictEqual(typeof payload.timestamp, 'number');
    assert.ok(payload.timestamp >= before && payload.timestamp <= after);
    assert.strictEqual(payload.is_media, false);
});
