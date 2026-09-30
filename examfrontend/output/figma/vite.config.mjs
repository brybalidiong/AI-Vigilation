import { defineConfig } from '../../node_modules/vite/dist/node/index.js';
import vue from '../../node_modules/@vitejs/plugin-vue/dist/index.mjs';
import { fileURLToPath } from 'node:url';
export default defineConfig({
  root: fileURLToPath(new URL('../../', import.meta.url)),
  plugins: [{name:'isolated-design-preview',enforce:'pre',transform(source,id){
    if(!id.endsWith('.vue') || !source.includes('<script setup>')) return;
    let script=source.match(/<script setup>([\s\S]*?)<\/script>/)?.[1];
    if(!script) return;
    const refs=[...script.matchAll(/const\s+(\w+)\s*=\s*ref\(/g)].map(m=>m[1]);
    script=script.replace(/import\s*\{([^}]+)\}\s*from\s*["']vue["']/g,(all,names)=>{
      let stubs=[];
      let updated=names.replace(/\b(onMounted|onUnmounted|watch)\b/g,name=>{stubs.push(`const ${name}=()=>{};`);return `${name} as __original_${name}`;});
      return `import {${updated}} from 'vue';\n${stubs.join('\n')}`;
    });
    script+=`\nconst __designRefs={${refs.join(',')}};\nfor(const [key,value] of Object.entries(window.__designState||{})){if(__designRefs[key])__designRefs[key].value=value;}\n`;
    if(id.includes('/views/') || id.includes('\\views\\'))script+='window.__designRefs=__designRefs;';
    return source.replace(/<script setup>[\s\S]*?<\/script>/,`<script setup>${script}</script>`);
  }},vue()],
  resolve:{alias:{'@':fileURLToPath(new URL('../../src',import.meta.url))}},
  server:{host:'127.0.0.1',port:5174,strictPort:true}
});
