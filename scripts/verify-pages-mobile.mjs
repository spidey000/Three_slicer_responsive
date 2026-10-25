// End-to-end smoke test against the live GitHub Pages deployment.
// Run with: npm i --no-save --no-package-lock playwright && npx playwright install chromium
//          node scripts/verify-pages-mobile.mjs
import { chromium } from 'playwright'
import fs from 'node:fs'

const url = process.env.PAGES_URL || 'https://spidey000.github.io/Three_slicer_responsive/'
const widths = [320, 360, 390, 430]
const output = 'pages-mobile-screenshots'
fs.mkdirSync(output, { recursive: true })

const browser = await chromium.launch({
  headless: true,
  args: [
    '--no-sandbox',
    '--enable-webgl',
    '--use-gl=angle',
    '--use-angle=swiftshader',
    '--enable-unsafe-swiftshader',
    '--disable-dev-shm-usage',
  ],
})

async function checkWidth(width) {
  const page = await browser.newPage({
    viewport: { width, height: 844 },
    deviceScaleFactor: 1,
    isMobile: true,
    hasTouch: true,
  })
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 })
    await page.waitForFunction(() => {
      const find = node => {
        if (node.querySelector?.('.empty-hint')) return node.querySelector('.empty-hint')
        for (const element of node.querySelectorAll?.('*') || []) {
          if (element.shadowRoot) {
            const found = find(element.shadowRoot)
            if (found) return found
          }
        }
        return null
      }
      return !!find(document)
    }, null, { timeout: 90000 })
    await page.waitForTimeout(1000)

    const geometry = await page.evaluate(() => {
      const find = node => {
        const matching = node.querySelector?.('.empty-hint')
        if (matching) return matching
        for (const element of node.querySelectorAll?.('*') || []) {
          if (element.shadowRoot) {
            const result = find(element.shadowRoot)
            if (result) return result
          }
        }
        return null
      }
      const card = find(document)
      const frame = card.getBoundingClientRect()
      const canvas = card.closest('.vp-canvas')?.getBoundingClientRect()
      const button = card.querySelector('button')?.getBoundingClientRect()
      return {
        viewport: window.innerWidth,
        card: { left:frame.left, right:frame.right, top:frame.top, bottom:frame.bottom, width:frame.width },
        canvas: canvas ? {left:canvas.left, right:canvas.right} : null,
        button: button ? {left:button.left, right:button.right} : null,
        visibility: getComputedStyle(card).visibility,
      }
    })
    await page.screenshot({ path: `${output}/mobile-${width}.png`, fullPage: true })
    const english = await page.evaluate(() => {
      const find = node => {
        const matching = node.querySelector?.('.empty-hint')
        if (matching) return matching
        for (const element of node.querySelectorAll?.('*') || []) {
          if (element.shadowRoot) {
            const result = find(element.shadowRoot)
            if (result) return result
          }
        }
        return null
      }
      const card = find(document)
      return {
        lang: document.documentElement.lang,
        title: card?.querySelector('.eh-title')?.textContent?.trim(),
        button: card?.querySelector('.eh-btn')?.textContent?.trim(),
      }
    })
    if (english.lang !== 'en' || english.title !== 'Your next project starts here' || english.button !== 'Open 3D model') {
      throw new Error(`English UI regression at ${width}px: ${JSON.stringify(english)}`)
    }
    if (width === 390) {
      await page.locator('.nav-setting').click()
      await page.waitForTimeout(150)
      const modal = page.locator('.settings-drawer')
      const modalContent = await modal.textContent()
      if (!modalContent.includes('Slicing settings') || !modalContent.includes('Print configuration')) {
        throw new Error('Mobile settings panel is not in English')
      }
      await page.screenshot({ path: `${output}/settings-mobile-${width}.png`, fullPage: true })
      await page.locator('.close-drawer').click()
    }

    const tolerance = 2
    const bounds = [geometry.card, geometry.button].filter(Boolean)
    for (const rect of bounds) {
      if (rect.left < -tolerance || rect.right > geometry.viewport + tolerance) {
        throw new Error(`Clipped at ${width}px: ${JSON.stringify(geometry)}`)
      }
    }
    if (geometry.card.width < 200 || geometry.visibility !== 'visible') {
      throw new Error(`Unexpected card dimensions at ${width}px: ${JSON.stringify(geometry)}`)
    }
    console.log(`PASS viewport=${width}px card=[${Math.round(geometry.card.left)},${Math.round(geometry.card.right)}] button=[${Math.round(geometry.button?.left)},${Math.round(geometry.button?.right)}]`)
  } catch (error) {
    await page.screenshot({ path: `${output}/mobile-${width}-error.png`, fullPage: true }).catch(() => {})
    throw error
  } finally {
    await page.close()
  }
}

try {
  for (const width of widths) await checkWidth(width)
  console.log(`PASS: all ${widths.length} mobile viewport sizes, live URL: ${url}`)
} finally {
  await browser.close()
}
