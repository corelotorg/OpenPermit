// SPDX-License-Identifier: Apache-2.0
// Execute the actual inline viewer; this DOM adapter is not a browser renderer.
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(process.argv[2], 'utf8');
const source = JSON.parse(html.match(/id="assembly">([\s\S]*?)<\/script>/)[1]);
const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
class Element {
  constructor() { this.children=[]; this.attrs={}; this.listeners={}; this.dataset={}; this.checked=true; this.value=0; this.textContent=''; }
  append(child) { this.children.push(child); }
  replaceChildren() { this.children=[]; }
  setAttribute(k,v) { this.attrs[k]=String(v); }
  addEventListener(k,f) { this.listeners[k]=f; }
  click() { if (this.listeners.click) this.listeners.click({target:this}); }
}
const nodes = Object.fromEntries(['assembly','drawing','parts','detail','progress','viewname','percentage','reset','play','export','counts','framing','sheathing','fasteners','summary','revision'].map(k=>[k,new Element()]));
nodes.assembly.textContent=JSON.stringify(source);
const blobs=[];
const context=vm.createContext({
  document:{getElementById:id=>nodes[id],createElement:()=>new Element(),createElementNS:()=>new Element()},
  Blob:class { constructor(parts){this.text=parts.join('');} },
  URL:{createObjectURL:b=>{blobs.push(b.text);return 'blob:probe';},revokeObjectURL:()=>{}},
  setTimeout:f=>f(),window:{matchMedia:()=>({matches:true})},performance:{now:()=>0}
});
vm.runInContext(scripts.at(-1)[1],context,{timeout:5000});
function snapshot(label) {
  nodes.export.click();
  return {label,view:nodes.viewname.textContent,percentage:nodes.percentage.textContent,
    artifact:JSON.parse(blobs.at(-1)),
    shapes:nodes.drawing.children.map(n=>({attrs:n.attrs,text:n.textContent})),
    partIds:nodes.parts.children.map(n=>n.dataset.id)};
}
const states=[snapshot('front')];
nodes.progress.value=100; nodes.progress.listeners.input(); states.push(snapshot('isometric'));
nodes.framing.checked=false;nodes.framing.listeners.change({target:nodes.framing});states.push(snapshot('framing-hidden'));
nodes.framing.checked=true;nodes.framing.listeners.change({target:nodes.framing});
nodes.fasteners.checked=true;nodes.fasteners.listeners.change({target:nodes.fasteners});states.push(snapshot('markers-visible'));
nodes.parts.children[3].click();const detail=JSON.parse(nodes.detail.textContent);
const details={};
for(const prefix of ['plate-', 'stud-', 'sheathing-', 'fastener-']) {
  nodes.parts.children.find(n=>n.dataset.id.split(':').at(-1).startsWith(prefix)).click();
  details[prefix]=JSON.parse(nodes.detail.textContent);
}
nodes.reset.click(); states.push(snapshot('reset'));
process.stdout.write(JSON.stringify({states,detail,details}));
