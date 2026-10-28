const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

function setup(){
  const elements=new Map(),pending=[];
  const document={getElementById(id){if(!elements.has(id))elements.set(id,{open:false,addEventListener(){}});return elements.get(id);},addEventListener(){}};
  const window={addEventListener(){}};
  const context=vm.createContext({document,window,fetch:()=>new Promise(resolve=>pending.push(resolve)),setInterval(){},clearInterval(){}});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/requests.js'),'utf8'),context);
  return {read:window.GradCompassRequests.read,pending,el:id=>document.getElementById(id)};
}
const response=(count,ok=true)=>({ok,json:async()=>({requests:[],attention_count:count,unassociated_delivery_errors:[],error:ok?undefined:'Obsolete failure'})});

test('a delayed Requests response cannot restore an obsolete attention indicator',async()=>{
  const ui=setup(),old=ui.read(),latest=ui.read();
  ui.pending[1](response(0));await latest;
  assert.equal(ui.el('open-requests').textContent,'Requests');
  ui.pending[0](response(1));await old;
  assert.equal(ui.el('open-requests').textContent,'Requests');assert.equal(ui.el('requests-notification').hidden,true);
});
test('an obsolete failed HTTP response does not override the latest healthy refresh',async()=>{
  const ui=setup(),old=ui.read(),latest=ui.read();
  ui.pending[1](response(0));await latest;ui.pending[0](response(1,false));await old;
  assert.equal(ui.el('requests-notification').hidden,true);
});
