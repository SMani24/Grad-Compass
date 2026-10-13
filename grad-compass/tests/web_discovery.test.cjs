const { test } = require('node:test');
const assert = require('node:assert/strict');
const { hasCoordinates, filterUniversities, safeExternalUrl, dominantLandmassBounds, discoveryGeometry } = require('../web/app.js');

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

test('country framing uses the main landmass without distant islands', () => {
  const geometry = require('../ui/data/countries.geo.json');
  const france = geometry.features.find(feature => feature.properties.name === 'France');
  assert.ok(france);
  const [[south, west], [north, east]] = dominantLandmassBounds(france);
  assert.ok(south > 40 && north < 52 && west > -6 && east < 10, 'France should frame Europe, rather than all overseas territory');
});
test('dateline-crossing land is framed locally rather than as a world-wide box', () => {
  const bounds = dominantLandmassBounds({ geometry: { type: 'Polygon', coordinates: [
    [[179, 10], [-179, 10], [-179, 12], [179, 12], [179, 10]]
  ] } });
  assert.deepEqual(bounds, [[10, 179], [12, 181]]);
});
test('unsupported or missing country geometry does not produce a camera target', () => {
  assert.equal(dominantLandmassBounds(null), null);
  assert.equal(dominantLandmassBounds({ geometry: { type: 'Point', coordinates: [0, 0] } }), null);
});
test('discovery excludes Antarctica using the bundled ISO field without dropping other territories or changing source geometry', () => {
  const geometry = require('../ui/data/countries.geo.json');
  const result = discoveryGeometry(geometry);
  assert.equal(result.features.length, geometry.features.length - 1);
  assert.ok(!result.features.some(feature => feature.properties.name === 'Antarctica'));
  assert.ok(result.features.some(feature => feature.properties['ISO3166-1-Alpha-3'] === 'ATF'));
  assert.ok(geometry.features.some(feature => feature.properties.name === 'Antarctica'));
});
