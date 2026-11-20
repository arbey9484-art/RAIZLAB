const metodo=document.getElementById('metodo');
function cambiar(){for(const nombre of ['biseccion','bairstow'])document.getElementById(nombre).hidden=metodo.value!==nombre;}
metodo.addEventListener('change',cambiar);cambiar();
const datos=document.getElementById('puntos');
if(datos){
 const canvas=document.getElementById('grafica'),ctx=canvas.getContext('2d'),W=canvas.width,H=canvas.height,m=55;
 const config=JSON.parse(document.getElementById('graph-function').textContent);
 const coord=document.getElementById('graph-coordinates'),status=document.getElementById('graph-status');
 let puntos=JSON.parse(datos.textContent),validos=puntos.filter(p=>p[1]!==null&&Number.isFinite(p[1]));
 let ymin=validos.length?Math.min(0,...validos.map(p=>p[1])):-1,ymax=validos.length?Math.max(0,...validos.map(p=>p[1])):1;
 if(ymin===ymax){ymin-=1;ymax+=1;}const margen=(ymax-ymin)*.08;
 const inicio={xmin:puntos[0][0],xmax:puntos.at(-1)[0],ymin:ymin-margen,ymax:ymax+margen};
 let vista={...inicio},cursor=null,arrastre=null,timer,controller,version=0;
 const X=x=>m+(x-vista.xmin)/(vista.xmax-vista.xmin)*(W-2*m);
 const Y=y=>H-m-(y-vista.ymin)/(vista.ymax-vista.ymin)*(H-2*m);
 const realX=p=>vista.xmin+(p-m)/(W-2*m)*(vista.xmax-vista.xmin);
 const realY=p=>vista.ymax-(p-m)/(H-2*m)*(vista.ymax-vista.ymin);
 const fmt=n=>Number(n.toPrecision(6)).toString();
 function posicion(e){const r=canvas.getBoundingClientRect();return{x:(e.clientX-r.left)*W/r.width,y:(e.clientY-r.top)*H/r.height};}
 function paso(rango){const p=10**Math.floor(Math.log10(rango/6)),a=rango/(6*p);return(a<=1?1:a<=2?2:a<=5?5:10)*p;}
 function dibujar(){
  ctx.clearRect(0,0,W,H);ctx.fillStyle='#fff';ctx.fillRect(0,0,W,H);ctx.font='13px Segoe UI';
  const dx=paso(vista.xmax-vista.xmin),dy=paso(vista.ymax-vista.ymin);
  ctx.lineWidth=1;ctx.strokeStyle='#e7e5f0';ctx.fillStyle='#526578';
  for(let x=Math.ceil(vista.xmin/dx)*dx,k=0;x<=vista.xmax&&k<30;x+=dx,k++){ctx.beginPath();ctx.moveTo(X(x),m);ctx.lineTo(X(x),H-m);ctx.stroke();ctx.fillText(fmt(x),Math.min(W-m-25,Math.max(m,X(x)-16)),H-m+23);}
  for(let y=Math.ceil(vista.ymin/dy)*dy,k=0;y<=vista.ymax&&k<30;y+=dy,k++){ctx.beginPath();ctx.moveTo(m,Y(y));ctx.lineTo(W-m,Y(y));ctx.stroke();ctx.fillText(fmt(y),3,Y(y)+4);}
  ctx.save();ctx.beginPath();ctx.rect(m,m,W-2*m,H-2*m);ctx.clip();ctx.strokeStyle='#8796aa';ctx.lineWidth=1.5;ctx.beginPath();ctx.moveTo(m,Y(0));ctx.lineTo(W-m,Y(0));ctx.moveTo(X(0),m);ctx.lineTo(X(0),H-m);ctx.stroke();
  ctx.strokeStyle='#7850ce';ctx.lineWidth=2.6;ctx.beginPath();let anterior=null;
  for(const [x,y] of puntos){if(y===null||!Number.isFinite(y)){anterior=null;continue;}const actual={x:X(x),y:Y(y)};
   // No unir saltos grandes entre muestras, por ejemplo alrededor de una asíntota.
   if(anterior&&Math.abs(actual.y-anterior.y)<H*1.5)ctx.lineTo(actual.x,actual.y);else ctx.moveTo(actual.x,actual.y);anterior=actual;
  }ctx.stroke();
  if(cursor){ctx.strokeStyle='#259e9a';ctx.setLineDash([4,4]);ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(cursor.x,m);ctx.lineTo(cursor.x,H-m);ctx.moveTo(m,cursor.y);ctx.lineTo(W-m,cursor.y);ctx.stroke();ctx.setLineDash([]);}
  ctx.restore();ctx.fillStyle='#526578';ctx.fillText('x',W-25,H-m+5);ctx.fillText('f(x)',10,24);
 }
 function actualizar(){clearTimeout(timer);controller?.abort();const v=++version;status.textContent='Actualizando curva…';timer=setTimeout(async()=>{
   controller=new AbortController();
   try{const r=await fetch('/api/grafica',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...config,xmin:vista.xmin,xmax:vista.xmax}),signal:controller.signal});const d=await r.json();if(!r.ok)throw Error(d.error||'No se pudo calcular la curva.');if(v!==version)return;puntos=d.puntos;status.textContent='';dibujar();}
   catch(e){if(e.name!=='AbortError'&&v===version)status.textContent='No se actualizó la curva. Comprueba que el servidor siga abierto o restablece la vista.';}
  },130);}
 function aplicar(nueva){const rx=nueva.xmax-nueva.xmin,ry=nueva.ymax-nueva.ymin;if(!Object.values(nueva).every(Number.isFinite)||rx<1e-10||ry<1e-10||Math.max(...Object.values(nueva).map(Math.abs))>1e12){status.textContent='Se alcanzó el rango de zoom disponible.';return;}vista=nueva;cursor=null;dibujar();actualizar();}
 function zoom(f,px=(W/2),py=(H/2)){const x=realX(px),y=realY(py);aplicar({xmin:x+(vista.xmin-x)*f,xmax:x+(vista.xmax-x)*f,ymin:y+(vista.ymin-y)*f,ymax:y+(vista.ymax-y)*f});}
 function reset(){aplicar({...inicio});coord.textContent='Vista inicial restaurada.';}
 document.getElementById('zoom-in').onclick=()=>zoom(.75);document.getElementById('zoom-out').onclick=()=>zoom(1/.75);document.getElementById('graph-reset').onclick=reset;
 canvas.addEventListener('wheel',e=>{e.preventDefault();const p=posicion(e);zoom(e.deltaY<0?.85:1/.85,p.x,p.y);},{passive:false});
 canvas.addEventListener('pointerdown',e=>{if(e.button!==0)return;canvas.focus();const p=posicion(e);arrastre={...p,vista:{...vista},id:e.pointerId};canvas.setPointerCapture(e.pointerId);});
 canvas.addEventListener('pointermove',e=>{const p=posicion(e);
  if(arrastre){const dx=(p.x-arrastre.x)/(W-2*m)*(arrastre.vista.xmax-arrastre.vista.xmin),dy=(p.y-arrastre.y)/(H-2*m)*(arrastre.vista.ymax-arrastre.vista.ymin);aplicar({xmin:arrastre.vista.xmin-dx,xmax:arrastre.vista.xmax-dx,ymin:arrastre.vista.ymin+dy,ymax:arrastre.vista.ymax+dy});return;}
  if(p.x<m||p.x>W-m||p.y<m||p.y>H-m){cursor=null;dibujar();return;}cursor=p;const x=realX(p.x),y=realY(p.y);let etiqueta=`Puntero: x = ${fmt(x)}; y = ${fmt(y)}`;
  const i=Math.round((x-puntos[0][0])/(puntos.at(-1)[0]-puntos[0][0])*(puntos.length-1));const muestra=puntos[i];
  if(muestra&&muestra[1]!==null)etiqueta+=` · Muestra cercana: f(${fmt(muestra[0])}) ≈ ${fmt(muestra[1])}`;
  coord.textContent=etiqueta;dibujar();
 });
 const soltar=()=>{arrastre=null;};canvas.addEventListener('pointerup',soltar);canvas.addEventListener('pointercancel',soltar);canvas.addEventListener('lostpointercapture',soltar);
 canvas.addEventListener('pointerleave',()=>{if(!arrastre){cursor=null;dibujar();}});
 canvas.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','=','-','0'].includes(e.key))return;e.preventDefault();if(e.key==='0')return reset();if(e.key==='+'||e.key==='=')return zoom(.75);if(e.key==='-')return zoom(1/.75);const dx=(vista.xmax-vista.xmin)*.15,dy=(vista.ymax-vista.ymin)*.15;const x=e.key==='ArrowLeft'?-dx:e.key==='ArrowRight'?dx:0,y=e.key==='ArrowDown'?-dy:e.key==='ArrowUp'?dy:0;aplicar({xmin:vista.xmin+x,xmax:vista.xmax+x,ymin:vista.ymin+y,ymax:vista.ymax+y});});
 dibujar();actualizar();
}
document.getElementById('imprimir')?.addEventListener('click',()=>window.print());
