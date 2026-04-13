const test = require('node:test');
const assert = require('node:assert');

test('Collector Module Structure', async (t) => {
    // We don't want to actually load index.js here without mocking process.env because it will throw
    // if API_KEY is not set. So let's just mock it or set it.
    process.env.API_KEY = 'test-key';
    const index = require('../src/index.js');

    await t.test('exports forwardToBackend', () => {
        assert.strictEqual(typeof index.forwardToBackend, 'function');
    });
});
