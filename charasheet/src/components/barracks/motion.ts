/**
 * The barracks' animation (not part of upstream charasheet): footlockers
 * that open before their sheet does, and new recruits' being carried in.
 * The look is in index.css; this decides when.
 */
import type { MouseEvent } from 'react'

/** How long opening a footlocker takes before the sheet shows (see sheet-rise in index.css). */
const OPEN_MS = 800
/** How recently a character joined for its footlocker to be carried in. */
const ARRIVING_MS = 2500

/**
 * The hub's Animate switch: readable here when the Barracks shares the hub's
 * storage (on the public site, where both are one origin). On otherwise.
 */
export function barracksAnimated(): boolean {
  try {
    return localStorage.getItem('hub.animate') !== 'off'
  } catch {
    return true
  }
}

/** Just created or imported, so its footlocker gets set down as it appears. */
export function isNewRecruit(createdAt: number): boolean {
  return Date.now() - createdAt < ARRIVING_MS
}

/**
 * For the Open link: open the footlocker it sits on, then go (the link's own
 * navigation is held back until then). A ctrl-, shift- or middle-click, or
 * animation switched off, goes straight on as a plain link.
 */
export function openFootlocker(event: MouseEvent<HTMLElement>, go: () => void): void {
  if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
  const locker = event.currentTarget.closest('.footlocker')
  if (!locker || !barracksAnimated()) return
  event.preventDefault()
  if (locker.classList.contains('opening')) return
  locker.classList.add('opening')
  window.setTimeout(go, OPEN_MS)
}
