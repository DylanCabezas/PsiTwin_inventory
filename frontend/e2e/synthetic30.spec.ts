import {test,expect} from '@playwright/test'
const out='../outputs/psitwin_pruebas/'
test('actual React map and historical charts against imported MongoDB',async({page,request})=>{
 const info=await (await request.get('http://127.0.0.1:18081/__test/status')).json()
 expect(info.productos).toHaveLength(30)
 await page.addInitScript(({tenant})=>{localStorage.setItem('psitwin.token','synthetic30-test-identity');localStorage.setItem('psitwin.sesion',JSON.stringify({rol:'EMPRESA',empresa:{id_empresa:tenant,nombre:'Empresa SINTÉTICA de pruebas'}}))},{tenant:info.empresa})
 const wid=info.almacen.id??info.almacen.id_almacen
 await page.goto(`/almacenes/${wid}/plano`)
 await expect(page.locator('[data-nivel]')).toHaveCount(10)
 await expect(page.locator('[data-estado="sin_datos"]')).toHaveCount(10)
 await expect(page.getByText('Helado de vainilla',{exact:false}).first()).toBeVisible()
 await expect(page.getByText('Rack C1',{exact:false})).toBeVisible()
 await page.screenshot({path:out+'plano_ABC1.png',fullPage:true})
 await page.goto('/analisis')
 await page.getByRole('button',{name:'Demanda registrada',exact:true}).click()
 await expect(page.getByRole('img',{name:/Demanda histórica/})).toBeVisible()
 const productSelect=page.getByLabel('Producto',{exact:true})
 for(const product of info.productos){
   await productSelect.selectOption(product.id_producto)
   await expect(page.getByText('396',{exact:true}).first()).toBeVisible()
   await expect(page.locator('svg polyline').first()).toBeVisible()
 }
 await page.screenshot({path:out+'demanda_diaria.png',fullPage:true})
 await page.getByLabel('Ver historial por').selectOption('semanal')
 await expect(page.getByText(/agrupación semanal/)).toBeVisible()
 await page.screenshot({path:out+'demanda_semanal.png',fullPage:true})
 await page.getByLabel('Ver historial por').selectOption('mensual')
 await expect(page.getByText(/agrupación mensual/)).toBeVisible()
 await page.screenshot({path:out+'demanda_mensual.png',fullPage:true})
})

test('existing AutoGluon runtime forecast in the real analysis page',async({page,request})=>{
 test.setTimeout(90000)
 page.setDefaultTimeout(15000)
 const info=await (await request.get('http://127.0.0.1:18081/__test/status')).json()
 const pid=info.productos.find((p:any)=>p.codigo==='SYN-001').id_producto
 const wid=info.almacen.id??info.almacen.id_almacen
 await page.addInitScript(({tenant})=>{localStorage.setItem('psitwin.token','synthetic30-test-identity');localStorage.setItem('psitwin.sesion',JSON.stringify({rol:'EMPRESA',empresa:{id_empresa:tenant,nombre:'Empresa SINTÉTICA'}}))},{tenant:info.empresa})
 await expect.poll(async()=>{
   const result=await (await request.get(`http://127.0.0.1:18081/api/v1/analisis/pronostico?id_almacen=${wid}&id_producto=${pid}`)).json()
   return result.estado
 },{timeout:60000,intervals:[3000,5000]}).toBe('DISPONIBLE')
 const result=await (await request.get(`http://127.0.0.1:18081/api/v1/analisis/pronostico?id_almacen=${wid}&id_producto=${pid}`)).json()
 expect(result.predicciones).toHaveLength(90)
 expect(result.predicciones[0].fecha).toBe('2026-10-29')
 console.log('Runtime: 90 fechas correctas. Abriendo Análisis.')
 await page.goto('/analisis')
 await page.getByRole('button',{name:'Demanda registrada',exact:true}).click()
 await page.getByLabel('Producto',{exact:true}).selectOption(pid)
 console.log('Papaya seleccionada. Abriendo pronósticos.')
 await page.getByRole('button',{name:'Pronósticos',exact:true}).click()
 console.log('Vista de pronósticos abierta.')
 await expect(page.getByRole('img',{name:/Demanda histórica/})).toBeVisible()
 await expect(page.getByText('Pronóstico medio',{exact:false}).first()).toBeVisible()
 await expect(page.getByText('1 series disponibles de 1',{exact:true})).toBeVisible()
 await page.screenshot({path:out+'pronostico_papaya_aplicacion.png',fullPage:true})
})
