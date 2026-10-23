const $ = id => document.getElementById(id);
let devices = [];
async function api(path, options={}) {
  const r = await fetch(path, {credentials:'same-origin', ...options,
    headers: {'Content-Type':'application/json', ...options.headers}});
  const body = await r.json().catch(()=>({detail:r.statusText}));
  if (!r.ok) throw new Error(typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail));
  return body;
}
function el(tag, cls='', text='') {
  const node = document.createElement(tag); if(cls) node.className=cls;
  node.textContent=text;return node;
}
const minutesSince = iso => iso ? (Date.now()-Date.parse(iso))/60000 : Infinity;
async function refresh() {
  try {
    const data=await api('/api/admin/devices'); devices=data.devices;
    $('device-count').textContent=devices.length;
    $('paired-count').textContent=devices.filter(d=>d.paired).length;
    $('online-count').textContent=devices.filter(d=>d.paired&&minutesSince(d.last_seen)<2).length;
    $('server-state').textContent='● Server online';
    const container=$('devices');container.replaceChildren();
    const selector=$('ask-device');const selected=selector.value;
    selector.replaceChildren(new Option('Default: Dhaka',''));
    if (!devices.length) container.append(el('div','placeholder','No devices yet. Flash the ESP32 and power it on.'));
    for (const d of devices) {
      if (d.paired) selector.add(new Option(d.name, d.id));
      const box=el('div','device');const top=el('div','device-main');
      const left=el('div');left.append(el('div','device-name',d.name),el('div','device-id',d.id));
      const active=d.paired&&minutesSince(d.last_seen)<2;
      top.append(left,el('span','state'+(!active?' pending':''),!d.paired?'● AWAITING PAIRING':active?'● ONLINE':'○ OFFLINE'));
      box.append(top,el('div','device-meta',`${d.city}  ·  ${d.firmware}  ·  ${d.timezone}`));
      if (d.paired) {
        const form=el('form','device-settings');
        const fields=el('div','device-controls');
        const definitions=[['Name','name',d.name],['City','city',d.city],['Latitude','latitude',d.latitude],['Longitude','longitude',d.longitude],['Timezone','timezone',d.timezone]];
        const inputs={};
        definitions.forEach(([label,key,value])=>{
          const wrapper=el('label','',label.toUpperCase());const inp=el('input');inp.value=value;inp.required=true;
          inp.type=['latitude','longitude'].includes(key)?'number':'text';if(inp.type==='number')inp.step='any';
          wrapper.append(inp);fields.append(wrapper);inputs[key]=inp;
        });
        const save=el('button','mini','Save settings ↗');save.type='submit';
        const message=el('div','message');form.append(fields,save,message);
        form.addEventListener('submit', async e=>{e.preventDefault();
          try {await api('/api/admin/devices/'+encodeURIComponent(d.id)+'/settings',{
            method:'POST',body:JSON.stringify({name:inputs.name.value,city:inputs.city.value,
              latitude:Number(inputs.latitude.value),longitude:Number(inputs.longitude.value),
              timezone:inputs.timezone.value})});message.textContent='Settings saved';await refresh();}
          catch(err){message.textContent=err.message;}
        });
        box.append(form);
      }
      container.append(box);
    }
    selector.value=selected;
  } catch(err){$('server-state').textContent='● Error: '+err.message;}
}
$('pair-form').addEventListener('submit',async e=>{
  e.preventDefault();$('pair-message').textContent='Pairing…';
  try {const result=await api('/api/admin/claim',{method:'POST',body:JSON.stringify({code:$('pair-code').value,name:$('pair-name').value})});
    $('pair-message').textContent='Paired: '+result.name;$('pair-code').value='';await refresh();}
  catch(err){$('pair-message').textContent=err.message;}
});
$('ask-form').addEventListener('submit',async e=>{
  e.preventDefault();$('answer').hidden=false;$('answer').textContent='Thinking…';
  try {const result=await api('/api/admin/ask',{method:'POST',body:JSON.stringify({text:$('ask-text').value,device_id:$('ask-device').value||null})});
    $('answer').textContent=result.answer;}
  catch(err){$('answer').textContent='Error: '+err.message;}
});
$('refresh').addEventListener('click',refresh);refresh();
