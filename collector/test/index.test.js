const test = require('node:test');
const assert = require('node:assert');

// Mock API_KEY before requiring index.js to prevent import-time crashes
process.env.API_KEY = 'test_key';
const { parseAllowedGroups } = require('../src/index.js');

test('parseAllowedGroups parses comma-separated string to Set', () => {
    const groups = parseAllowedGroups('group1,group2,group3');
    assert.strictEqual(groups instanceof Set, true);
    assert.strictEqual(groups.size, 3);
    assert.strictEqual(groups.has('group1'), true);
    assert.strictEqual(groups.has('group2'), true);
    assert.strictEqual(groups.has('group3'), true);
    assert.strictEqual(groups.has('group4'), false);
});

test('parseAllowedGroups handles undefined or empty string', () => {
    const undefinedGroups = parseAllowedGroups(undefined);
    assert.strictEqual(undefinedGroups instanceof Set, true);
    assert.strictEqual(undefinedGroups.size, 0);

    const emptyGroups = parseAllowedGroups('');
    assert.strictEqual(emptyGroups instanceof Set, true);
    assert.strictEqual(emptyGroups.size, 0);
});

test('parseAllowedGroups handles single group', () => {
    const groups = parseAllowedGroups('single_group');
    assert.strictEqual(groups instanceof Set, true);
    assert.strictEqual(groups.size, 1);
    assert.strictEqual(groups.has('single_group'), true);
});
