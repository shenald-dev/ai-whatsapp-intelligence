const { test } = require('node:test');
const assert = require('node:assert');
const { parseAllowedGroups } = require('../src/index');

test('parseAllowedGroups with no input', () => {
    const groups = parseAllowedGroups(undefined);
    assert.strictEqual(groups.size, 0);
});

test('parseAllowedGroups with empty string', () => {
    const groups = parseAllowedGroups('');
    assert.strictEqual(groups.size, 0);
});

test('parseAllowedGroups with one group', () => {
    const groups = parseAllowedGroups('group1');
    assert.strictEqual(groups.size, 1);
    assert.ok(groups.has('group1'));
});

test('parseAllowedGroups with multiple groups', () => {
    const groups = parseAllowedGroups('group1,group2,group3');
    assert.strictEqual(groups.size, 3);
    assert.ok(groups.has('group1'));
    assert.ok(groups.has('group2'));
    assert.ok(groups.has('group3'));
});
