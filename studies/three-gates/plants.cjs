// Driftless adapters and a new willow/reed motif. The vendor engine remains unchanged.
'use strict';
const fs=require('fs'),vm=require('vm'),path=require('path');
const text=fs.readFileSync(path.join(__dirname,'vendor/driftless-engine.js'),'utf8');
const marker='const API = { generate,';
if(!text.includes(marker)) throw new Error('Pinned Driftless API changed');
const sandbox={module:{exports:{}},console};
vm.runInNewContext(text.replace(marker,'const API = { Scene, Rng, pine, tuft, plant, post, generate,'),sandbox);
const E=sandbox.module.exports,round=v=>Math.round(v*1000)/1000;
function scene(seed,W=260,H=260){
 const sc=new E.Scene({seed,W,H,density:.85,imperfection:.20,penWidth:.18,textZone:'none'});
 sc.comp={season:'summer',time:'day',lightX:-1,crownStyle:'hatch'};
 const ops=[],m=sc.mask;
 const fill=m.fillRings.bind(m),stamp=m.stamp.bind(m),vary=m.stampVar.bind(m),disc=m.disc.bind(m);
 m.fillRings=r=>{ops.push({t:'rings',rings:r.map(q=>Array.from(q,round))});fill(r);};
 m.stamp=(p,w)=>{ops.push({t:'stamp',pts:Array.from(p,round),w:round(w)});stamp(p,w);};
 m.stampVar=(p,ws)=>{ops.push({t:'var',pts:Array.from(p,round),ws:Array.from(ws,round)});vary(p,ws);};
 m.disc=(cx,cy,r)=>{ops.push({t:'disc',cx:round(cx),cy:round(cy),r:round(r)});disc(cx,cy,r);};
 sc.ops=ops;return sc;
}
function patch(sc,extra={}){return Object.assign({strokes:E.post(sc).map(s=>({pen:s.p,kind:s.k,pts:Array.from(s.pts,round)})),occluders:sc.ops},extra);}
function curve(a,b,c,n=24){let out=[];for(let i=0;i<=n;i++){let t=i/n,u=1-t;out.push(u*u*a[0]+2*u*t*b[0]+t*t*c[0],u*u*a[1]+2*u*t*b[1]+t*t*c[1]);}return out;}
function leaf(sc,x,y,L,side){
 const p=[x,y,x+side*L*.32,y+L*.24,x+side*L*.29,y+L*.64,x+side*L*.10,y+L,x+side*L*.02,y+L*.54,x,y];
 sc.line(p,1,0);sc.fill(p);
}
function willow(sc){
 const r=sc.rng('hanging-willow'),fronds=[];
 // Branch tips describe a spreading crown. Hanging fronds keep gaps between leaf ribbons.
 const tips=[[-85,104],[-64,75],[-44,51],[-20,34],[7,29],[32,43],[57,67],[78,99],[94,126]];
 for(const [dx,dy] of tips){
  for(let j=0;j<13;j++){
   const sx=130+dx+r.range(-8,8),sy=dy+r.range(-5,14),L=r.range(53,100)*(1-Math.abs(dx)/230);
   fronds.push({sx,sy,L,lean:r.range(-8,15),front:r.chance(.57)});
  }
 }
 function drawF(f){
  const p=curve([f.sx,f.sy],[f.sx+f.lean*.7,f.sy+f.L*.55],[f.sx+f.lean,f.sy+f.L]);
  // Leaves nearest the viewer are drawn before their stems, through the engine's local mask.
  for(let i=4;i<24;i+=2){const x=p[2*i],y=p[2*i+1];leaf(sc,x,y,r.range(3.5,6),i%4?-1:1);}
  sc.line(p,1,0);sc.halo(p,.55);
 }
 fronds.filter(f=>f.front).sort((a,b)=>b.sy+b.L-a.sy-a.L).forEach(drawF);
 // Broad forked trunk: two outline curves and short bark marks, with a real occlusion silhouette.
 const trunk=[122,245,122,211,119,181,125,147,130,116,136,146,132,181,134,211,136,245];
 sc.line(trunk.slice(0,10),0,0);sc.line(trunk.slice(8),0,0);
 for(let j=0;j<7;j++){
  let x=125+j*.85;sc.line(curve([x,240],[x-4,200],[x+1,162+r.range(-5,12)],19),0,1);
 }
 sc.fill(trunk);
 for(const [dx,dy] of tips){
  const p=curve([129,166],[132+dx*.25,dy+24],[130+dx,dy],30);
  sc.line(p,0,0);sc.halo(p,Math.max(1.2,4.8-Math.abs(dx)*.027));
 }
 fronds.filter(f=>!f.front).sort((a,b)=>b.sy+b.L-a.sy-a.L).forEach(drawF);
 return patch(sc,{origin:[130,245],height:216,kind:'willow',source:'new willow motif through Driftless Scene and mask'});
}
function reed(sc,i){
 const r=sc.rng('reed'),wind=r.range(-.28,.36);
 for(let k=0;k<r.int(3,6);k++){
  const x=20+r.range(-2,2),h=r.range(17,31),lean=r.range(-3,3)+wind*7;
  const p=curve([x,42],[x+lean*.3,42-h*.55],[x+lean,42-h],18);
  const a=p.length-2,hx=p[a],hy=p[a+1];
  if((i+k)%3===0){
   const cap=[hx-.65,hy+3,hx-.7,hy-1,hx,hy-2,hx+.7,hy-1,hx+.65,hy+3,hx-.65,hy+3];
   sc.line(cap,0,0);sc.fill(cap);
   for(let q=0;q<3;q++)sc.line([hx-.4+q*.35,hy+2.3,hx-.4+q*.35,hy-.6],0,1);
  }else{
   for(let q=0;q<4;q++){const y=hy+q*.8;sc.line([hx-1.4+q*.2,y-.4,hx,y,hx+1.3-q*.15,y-.6],1,0);}
  }
  sc.line(p,1,0);sc.halo(p,.5);
 }
 E.tuft(sc,20,42,r.range(10,18),wind,r,1,3.4);
 return patch(sc,{kind:'reed',wind,origin:[20,42]});
}
const plants=[];
for(let i=0;i<24;i++)plants.push(reed(scene('three-gates-reed-'+i,45,48),i));
for(let i=0;i<24;i++){
 const sc=scene('three-gates-grass-'+i,45,48),r=sc.rng('grass');
 E.tuft(sc,20,42,r.range(10,21),r.range(-.3,.4),r,1,r.range(2.5,4.5));
 if(i%4===0)E.plant(sc,'umbel',20,42,22,.15,.7,r,1,false);
 plants.push(patch(sc,{kind:i%4===0?'umbel':'grass',origin:[20,42]}));
}
const pine=scene('three-gates-pine');E.pine(pine,130,245,173,{});
const out={generator:'Driftless Plates '+E.version,willow:willow(scene('three-gates-willow')),pine:patch(pine,{origin:[130,245],height:173,kind:'pine'}),plants};
fs.writeFileSync(path.join(__dirname,'output/plants.json'),JSON.stringify(out));
console.log({willowPaths:out.willow.strokes.length,pinePaths:out.pine.strokes.length,plantVariants:plants.length});
