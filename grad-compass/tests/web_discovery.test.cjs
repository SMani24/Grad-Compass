const { test } = require('node:test');
const assert = require('node:assert/strict');
const { hasCoordinates, filterUniversities, safeExternalUrl } = require('../web/app.js');

const universities = [
  { id: 1, name: 'Northbridge Example', city: 'Example City', country_code: 'CAN', status: 'Researching', latitude: 0, longitude: 0 },
  { id: 2, name: 'Rivergate Example', city: 'Other City', country_code: 'DEU', status: 'Applying', latitude: 52.5, longitude: 13.4 },
  { id: 3, name: 'Unlocated Example', city: null, country_code: 'CAN', status: 'Researching', latitude: null, longitude: null }
];

test('shared map/list filtering combines country, stage, and case-insensitive search', () => {
  assert.deepEqual(filterUniversities(universities, { country: 'CAN', status: 'Researching', search: '  NORTH  ' }).map(u => u.id), [1]);
  assert.deepEqual(filterUniversities(universities, { search: 'other city' }).map(u => u.id), [2]);
  assert.deepEqual(filterUniversities(universities, { country: 'USA' }), []);
});
test('unlocated universities remain in search results', () => {
  assert.deepEqual(filterUniversities(universities, { country: 'CAN' }).map(u => u.id), [1, 3]);
});
test('valid zero coordinates are accepted but invalid/non-numeric coordinates are not', () => {
  assert.equal(hasCoordinates(universities[0]), true);
  assert.equal(hasCoordinates(universities[2]), false);
  for (const latitude of [NaN, Infinity, 91, '0']) assert.equal(hasCoordinates({ latitude, longitude: 0 }), false);
  assert.equal(hasCoordinates({ latitude: 0, longitude: -181 }), false);
});
test('external links allow only explicit HTTP/HTTPS URLs', () => {
  assert.equal(safeExternalUrl('https://example.invalid/program'), 'https://example.invalid/program');
  for (const value of ['javascript:alert(1)', 'file:///private/profile.json', '//example.invalid', 'data:text/html,example', '']) assert.equal(safeExternalUrl(value), null);
});
