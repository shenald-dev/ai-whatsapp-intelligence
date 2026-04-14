const { test } = require('node:test');
const assert = require('node:assert');

test('collector index module exports functions and does not hang process', () => {
    // Before our fix, simply requiring the module would start the client and hang the process
    const collector = require('../src/index.js');

    assert.ok(collector.client, 'Expected client to be exported');
    assert.ok(collector.forwardToBackend, 'Expected forwardToBackend to be exported');
});
