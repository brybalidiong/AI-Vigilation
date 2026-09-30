const manifest=await (await fetch('./manifest.json')).json();
const plan=manifest.groups.flatMap(g=>g.frames.map(f=>({...f,page:g.page})));
const frame=document.querySelector('#preview');const output=document.querySelector('#result');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const props=['backgroundColor','backgroundImage','color','borderTopColor','borderRightColor','borderBottomColor','borderLeftColor','borderTopWidth','boxShadow','transform','opacity'];
const read=(w,e)=>{const c=w.getComputedStyle(e);return Object.fromEntries(props.map(p=>[p,c[p]]));};
const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height};};
const text=e=>(e.textContent||'').replace(/\s+/g,' ').trim();
const result=[];
for(let index=0;index<plan.length;index++){
 const item=plan[index];frame.style.width=item.width+'px';frame.style.height=item.height+'px';
 frame.src='./preview.html?screen='+encodeURIComponent(item.screen);
 await new Promise(r=>frame.onload=r);const w=frame.contentWindow,d=frame.contentDocument;
 for(let i=0;i<100&&!w.__designReady;i++)await sleep(50);
 await d.fonts.ready;await sleep(100);
 const roots=new Set();let css='';
 const visit=rules=>{let result='';for(const rule of rules){if(rule.selectorText){for(const selector of rule.selectorText.split(',')){if(!selector.includes(':hover'))continue;const root=selector.slice(0,selector.indexOf(':hover'));try{for(const e of d.querySelectorAll(root))roots.add(e);}catch{}}
 result+=rule.cssText.replaceAll(':hover','.__designHover')+'\n';
 }else if(rule.cssRules){const opening=rule.cssText.slice(0,rule.cssText.indexOf('{')+1);result+=opening+visit(rule.cssRules)+'}\n';}else result+=rule.cssText+'\n';}return result;};
 for(const sheet of d.styleSheets){try{css+=visit(sheet.cssRules);}catch{}}
 for(const e of d.querySelectorAll('[onmouseover]'))roots.add(e);
 const timing=new Map([...roots].map(e=>{const c=w.getComputedStyle(e);return [e,{duration:c.transitionDuration,easing:c.transitionTimingFunction}];}));
 const style=d.createElement('style');style.textContent=css+'\n*{transition:none!important;animation:none!important}';d.head.appendChild(style);
 const controls=[];
 for(const root of roots){if(root.matches(':disabled'))continue;const bounds=rect(root);if(bounds.w<1||bounds.h<1)continue;
 const elements=[root,...root.querySelectorAll('*')];const before=elements.map(e=>({style:read(w,e),bounds:rect(e)}));
 root.classList.add('__designHover');root.dispatchEvent(new w.MouseEvent('mouseover',{bubbles:false}));const changes=[];
 for(let i=0;i<elements.length;i++){const e=elements[i],after=read(w,e);const change={};for(const p of props)if(after[p]!==before[i].style[p])change[p]=after[p];if(Object.keys(change).length)changes.push({root:i===0,tag:e.tagName,class:e.className?.baseVal??e.className,text:text(e),bounds:before[i].bounds,before:before[i].style,after,change});}
 const transition=w.getComputedStyle(root);root.dispatchEvent(new w.MouseEvent('mouseout',{bubbles:false}));root.classList.remove('__designHover');
 if(changes.length)controls.push({tag:root.tagName,class:root.className?.baseVal??root.className,text:text(root),bounds,timing:timing.get(root),changes});
 }
 const targets=[...d.querySelectorAll('button,a,[role="button"]')].filter(e=>{const r=rect(e);return r.w>0&&r.h>0&&!e.matches(':disabled');}).map(e=>({tag:e.tagName,id:e.id,class:e.className?.baseVal??e.className,text:text(e),href:e.getAttribute('href'),bounds:rect(e)}));
 result.push({...item,controls,targets});document.querySelector('#status').textContent='Inspected '+(index+1)+' / '+plan.length;output.textContent=JSON.stringify(result);
}
document.querySelector('#status').textContent='COMPLETE '+result.length;
