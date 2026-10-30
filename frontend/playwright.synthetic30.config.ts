import {defineConfig} from '@playwright/test'
export default defineConfig({
 testDir:'./e2e',testMatch:'synthetic30.spec.ts',workers:1,timeout:120000,
 use:{baseURL:'http://127.0.0.1:15174',channel:'msedge',headless:true,viewport:{width:1440,height:1000}},
 outputDir:'../outputs/psitwin_pruebas/playwright',reporter:[['list'],['json',{outputFile:'../outputs/psitwin_pruebas/playwright_results.json'}]],
 webServer:process.env.PSITWIN_SYNTHETIC30_EXTERNAL ? undefined : [
 {command:'..\\.runtime.local\\python\\python.exe -m uvicorn tests.synthetic30_browser_app:app --app-dir ../backend --host 127.0.0.1 --port 18081',url:'http://127.0.0.1:18081/__test/status',env:{PSITWIN_SYNTHETIC30_BROWSER:'1',MQTT_ENABLED:'false',EMAIL_ENABLED:'false'},timeout:60000},
 {command:'npm.cmd run dev -- --host 127.0.0.1 --port 15174 --strictPort',url:'http://127.0.0.1:15174',env:{VITE_PROXY_TARGET:'http://127.0.0.1:18081',VITE_API_URL:'/api/v1'},timeout:60000}
 ]
})
