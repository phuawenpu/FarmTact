import { useRef, useState } from 'react'

/** Keep the reader's position when a detail card returns to its parent. */
export function useCardView(initial = 'index') {
  const [view, update] = useState(initial)
  const origins = useRef(new Map<string, { scroll: number; label: string; element: HTMLElement | null }>())
  const capture = () => {
    const element = document.activeElement instanceof HTMLElement ? document.activeElement : null
    if (!element?.closest('.integrated-tool')) return
    origins.current.set(view, { scroll: window.scrollY, label: element?.getAttribute('aria-label') || element?.textContent?.trim() || '', element })
  }
  const navigate = (next: string) => {
    capture()
    update(next)
  }
  const restore = (next: string) => {
    const origin = origins.current.get(next)
    update(next)
    if (!origin) return
    requestAnimationFrame(() => requestAnimationFrame(() => {
      const visible = (element: HTMLElement) => element.getClientRects().length > 0
      const matches = (element: HTMLElement) => visible(element) && (element.getAttribute('aria-label') || element.textContent?.trim() || '') === origin.label
      const focus = origin.element?.isConnected && matches(origin.element) ? origin.element
        : Array.from(document.querySelectorAll<HTMLElement>('.integrated-tool button, .integrated-tool input, .integrated-tool select, .integrated-tool textarea')).find(matches)
      focus?.focus({ preventScroll: true })
      window.scrollTo(0, origin.scroll)
    }))
  }
  return [view, navigate, restore, capture] as const
}
