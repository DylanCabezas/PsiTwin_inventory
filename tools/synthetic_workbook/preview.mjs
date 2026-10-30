import fs from 'node:fs/promises';
import {Workbook} from '@oai/artifact-tool';
const dir=new URL('../../outputs/psitwin_pruebas/',import.meta.url);
const data=JSON.parse(await fs.readFile(new URL('dataset.json',dir),'utf8'));
for(const [name,rows] of Object.entries(data)){
 const wb=Workbook.create(),sh=wb.worksheets.add(name),keys=Object.keys(rows[0]).slice(0,6);
 const values=[keys,...rows.slice(0,6).map(r=>keys.map(k=>r[k]))];
 sh.getRange(`A1:F${values.length}`).values=values;
 sh.getRange(`A1:F${values.length}`).format.columnWidth=25;
 sh.getRange(`A1:F${values.length}`).format.wrapText=true;
 sh.getRange(`A1:F${values.length}`).format.rowHeight=45;
 sh.getRange('A1:F1').format={fill:'#163D50',font:{bold:true,color:'#FFFFFF'},rowHeight:38};
 if(name==='README'){sh.getRange('A2:F2').format.rowHeight=180;}
 const blob=await wb.render({sheetName:name,range:`A1:F${values.length}`,scale:1});
 await fs.writeFile(new URL(`preview_${name}.png`,dir),new Uint8Array(await blob.arrayBuffer()));
 console.log(name);
}
