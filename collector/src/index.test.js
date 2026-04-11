const test = require('node:test');
const assert = require('node:assert');
const { client, forwardToBackend } = require('./index.js');

test('Collector Module Exports', (t) => {
    assert.ok(client, 'client should be exported');
    assert.ok(forwardToBackend, 'forwardToBackend should be exported');
    assert.strictEqual(typeof forwardToBackend, 'function', 'forwardToBackend should be a function');
});
