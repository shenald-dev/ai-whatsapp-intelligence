const test = require('node:test');
const assert = require('node:assert');
const Module = require('node:module');

// Set up environment variables before requiring the module
process.env.API_KEY = 'test-api-key';
process.env.BACKEND_URL = 'http://test-backend/api/v1/ingest';

// Mocking dependencies since node_modules might be missing or we want to avoid side effects
const originalRequire = Module.prototype.require;

const mocks = {
    'axios': {
        post: async () => ({ status: 200, data: {} })
    },
    'whatsapp-web.js': {
        Client: class {
            on() {}
            initialize() {}
        },
        LocalAuth: class {}
    },
    'qrcode-terminal': {
        generate: () => {}
    },
    'dotenv': {
        config: () => {}
    }
};

// Use a safer mocking approach by wrapping the hijacking in a lifecycle hook if possible,
// but since we are using node:test and need to mock 'require' before the module is loaded,
// we will ensure we restore it.
Module.prototype.require = function(path) {
    if (mocks[path]) {
        return mocks[path];
    }
    return originalRequire.apply(this, arguments);
};

// Now require the module under test
const { forwardToBackend } = require('../src/index.js');

test.after(() => {
    // Restore original require
    Module.prototype.require = originalRequire;
});

test('forwardToBackend success path', async (t) => {
    const logMock = t.mock.method(console, 'log', () => {});

    const payload = {
        group_name: 'Test Group',
        sender_name: 'Test User',
        content: 'Hello World'
    };

    await forwardToBackend(payload);

    assert.strictEqual(logMock.mock.callCount(), 1);
    const logMessage = logMock.mock.calls[0].arguments[0];
    // Escaped the pipe character to match it literally
    assert.match(logMessage, /\[SENT\] Test Group \| Test User: Hello World/);
});

test('forwardToBackend error path', async (t) => {
    const errorMock = t.mock.method(console, 'error', () => {});

    // Override axios.post to fail for this test
    const originalPost = mocks['axios'].post;
    mocks['axios'].post = async () => {
        throw new Error('Network Error');
    };

    const payload = {
        group_name: 'Test Group',
        sender_name: 'Test User',
        content: 'Hello World'
    };

    try {
        await forwardToBackend(payload);

        assert.strictEqual(errorMock.mock.callCount(), 1);
        const errorMessage = errorMock.mock.calls[0].arguments[0];
        assert.strictEqual(errorMessage, '[FAILED] Sending to backend: Network Error');
    } finally {
        // Restore axios.post
        mocks['axios'].post = originalPost;
    }
});
