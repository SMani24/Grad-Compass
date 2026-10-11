const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

// A small DOM double exercises controller events and API calls without a desktop window.
class Element {
  constructor() {
    this.listeners = {};
    this.children = [];
    this.parts = {};
    this.attrs = {};
    this.value = "";
    this.checked = false;
    this.style = {};
    this.classList = { add() {}, remove() {}, toggle() {} };
  }
  addEventListener(name, fn) { this.listeners[name] = fn; }
  setAttribute(key, value) { this.attrs[key] = value; }
  getAttribute(key) { return this.attrs[key]; }
  set innerHTML(value) { this.html = value; this.children = []; }
  get innerHTML() { return this.html; }
  appendChild(element) { this.children.push(element); }
  querySelector(selector) {
    if (selector.startsWith('.entity-card')) return this.children.find(c => Number(c.attrs['data-id']) === Number(selector.match(/\d+/)[0]));
    return this.parts[selector] ||= new Element();
  }
  querySelectorAll(selector) {
    if (selector === '.entity-card') return this.children;
    if (selector === '.uni-card-check') return this.children.map(c => c.querySelector(selector));
    return [];
  }
}

function setup(getUniversities) {
  const elements = new Map();
  const ready = [];
  let confirmation;
  const mutations = [];
  const document = {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, new Element());
      return elements.get(id);
    },
    createElement() { return new Element(); },
    addEventListener(type, callback) { if (type === 'DOMContentLoaded') ready.push(callback); }
  };
  const window = {
    pywebview: { api: {
      get_universities: getUniversities,
      async delete_universities_batch(ids) { mutations.push({ type: 'delete', ids: [...ids] }); },
      async batch_update_university_status(ids, status) { mutations.push({ type: 'status', ids: [...ids], status }); }
    } },
    Modals: { showConfirm(value) { confirmation = value; } }
  };
  const context = vm.createContext({ document, window, console });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../ui/js/country_drawer.js'), 'utf8'), context);
  ready.forEach(callback => callback());
  return {
    window, mutations,
    el: id => document.getElementById(id),
    confirm: () => confirmation,
    select(index = 0) {
      const checkbox = document.getElementById('country-uni-list').children[index].querySelector('.uni-card-check');
      checkbox.checked = true;
      checkbox.listeners.click({ stopPropagation() {} });
    }
  };
}

test('switching countries cannot delete an invisible selection', async () => {
  const ui = setup(async code => [{ id: code === 'AAA' ? 1 : 2, name: 'Invented University' }]);
  await ui.window.CountryDrawer.load('AAA', 'Country A');
  ui.select();
  await ui.window.CountryDrawer.load('BBB', 'Country B');
  ui.el('btn-batch-delete').listeners.click();
  assert.equal(ui.confirm(), undefined);
  ui.select();
  ui.el('btn-batch-delete').listeners.click();
  await ui.confirm().onConfirm();
  assert.deepEqual(ui.mutations, [{ type: 'delete', ids: [2] }]);
});

test('switching countries cannot update an invisible selection', async () => {
  const ui = setup(async code => [{ id: code === 'AAA' ? 1 : 2, name: 'Invented University' }]);
  await ui.window.CountryDrawer.load('AAA', 'Country A');
  ui.select();
  await ui.window.CountryDrawer.load('BBB', 'Country B');
  ui.el('select-batch-status').value = 'Submitted';
  await ui.el('select-batch-status').listeners.change();
  assert.deepEqual(ui.mutations, []);
});

test('reload preserves visible selections but removes deleted IDs', async () => {
  let records = [{ id: 1, name: 'First' }, { id: 2, name: 'Second' }];
  const ui = setup(async () => records);
  await ui.window.CountryDrawer.load('AAA', 'Country A');
  ui.select(0); ui.select(1);
  records = [records[1]];
  await ui.window.CountryDrawer.load('AAA', 'Country A');
  ui.el('btn-batch-delete').listeners.click();
  await ui.confirm().onConfirm();
  assert.deepEqual(ui.mutations[0].ids, [2]);
});

test('late results from a previous country cannot replace the current list', async () => {
  let finishFirst;
  const ui = setup(code => code === 'AAA' ? new Promise(resolve => { finishFirst = resolve; }) : Promise.resolve([{ id: 2, name: 'Second' }]));
  const first = ui.window.CountryDrawer.load('AAA', 'Country A');
  await ui.window.CountryDrawer.load('BBB', 'Country B');
  finishFirst([{ id: 1, name: 'First' }]);
  await first;
  assert.equal(ui.el('country-uni-list').children[0].attrs['data-id'], 2);
});

test('loading another country removes stale cards and blocks old checkbox events', async () => {
  let finishSecond;
  const ui = setup(code => code === 'AAA' ? Promise.resolve([{ id: 1, name: 'First' }]) : new Promise(resolve => { finishSecond = resolve; }));
  await ui.window.CountryDrawer.load('AAA', 'Country A');
  const staleCheckbox = ui.el('country-uni-list').children[0].querySelector('.uni-card-check');
  const second = ui.window.CountryDrawer.load('BBB', 'Country B');
  assert.equal(ui.el('country-uni-list').children.length, 0);
  staleCheckbox.checked = true;
  staleCheckbox.listeners.click({ stopPropagation() {} });
  ui.el('btn-batch-delete').listeners.click();
  assert.equal(ui.confirm(), undefined);
  finishSecond([{ id: 2, name: 'Second' }]);
  await second;
  ui.el('btn-batch-delete').listeners.click();
  assert.equal(ui.confirm(), undefined);
});

test('failed loads show a retry message without leaving a hidden selection', async () => {
  let fail = false;
  const ui = setup(async () => {
    if (fail) throw new Error('Invented failure');
    return [{ id: 1, name: 'First' }];
  });
  await ui.window.CountryDrawer.load('AAA', 'Country A');
  ui.select();
  fail = true;
  await ui.window.CountryDrawer.load('AAA', 'Country A');
  assert.match(ui.el('country-uni-list').innerHTML, /Could not load universities/);
  ui.el('btn-batch-delete').listeners.click();
  assert.equal(ui.confirm(), undefined);
});
