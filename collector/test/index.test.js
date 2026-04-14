const test = require('node:test');
const assert = require('node:assert');

test('Collector exports main components for testability', () => {
    process.env.API_KEY = 'test_api_key';
    const { client, forwardToBackend } = require('../src/index.js');
    assert.ok(client, 'Client should be exported');
    assert.strictEqual(typeof forwardToBackend, 'function', 'forwardToBackend should be exported as a function');
});
