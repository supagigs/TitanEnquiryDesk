import { copyFileSync, mkdirSync } from 'node:fs'
mkdirSync('../titan_desk/www', { recursive: true })
copyFileSync('../titan_desk/public/frontend/index.html', '../titan_desk/www/titan-desk.html')
console.log('copied index.html -> titan_desk/www/titan-desk.html')
