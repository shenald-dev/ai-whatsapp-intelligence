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
    },
    post: async (url, payload, config) => {
        axiosPostCalledWith = { url, payload, config };
        return { status: 200 };
    }
};

// We need to inject the environment variable BEFORE requiring the script
process.env.API_KEY = 'test_key';

const { parseAllowedGroups, forwardToBackend } = proxyquire('../src/index.js', {
    'axios': axiosMock,
    'whatsapp-web.js': {
        Client: class {
            on() {}
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

test('forwardToBackend handles payload with undefined content gracefully without crashing', async () => {
    const payload = {
        group_name: 'Test Group',
        sender_name: 'Alice',
        content: undefined
    };

    // Reset our mock state
    axiosPostCalledWith = null;

    // This should not throw an error (e.g., from .substring on undefined)
    await forwardToBackend(payload);

    assert.ok(axiosPostCalledWith !== null, 'axios.post was not called');
    assert.strictEqual(axiosPostCalledWith.payload, payload);
});