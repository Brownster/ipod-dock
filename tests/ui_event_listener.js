process.on("unhandledRejection", () => {});
const fs = require('fs');
const vm = require('vm');
const { JSDOM } = require('jsdom');

const html = fs.readFileSync('ipod_sync/templates/index.html', 'utf8');
const dom = new JSDOM(html, { runScripts: 'outside-only' });
const window = dom.window;
window.fetch = () => Promise.resolve({ json: () => ({ detail: 'unauthorized' }) });
window.localStorage = { getItem: () => null };

vm.runInContext(fs.readFileSync('ipod_sync/static/app.js', 'utf8'), dom.getInternalVMContext());

(async () => {
  try { await window.initializeApp(); } catch (e) {}
  const fileInput = window.document.getElementById('file-input');
  let clicked = false;
  fileInput.click = () => { clicked = true; };
  window.document.getElementById('upload-area').dispatchEvent(new window.Event('click'));
  console.log(clicked ? 'ok' : 'fail');
})();

