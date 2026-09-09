export type EditionId = `v${number}`

const EDITION_PATH = /^\/(v[1-9][0-9]*)(?:\/|$)/

export function editionFromPath(pathname = window.location.pathname): EditionId | null {
  return pathname.match(EDITION_PATH)?.[1] as EditionId | undefined || null
}

export function editionBase(pathname = window.location.pathname): string {
  const edition = editionFromPath(pathname)
  return edition ? `/${edition}` : ''
}

export function editionPath(path: string, pathname = window.location.pathname): string {
  if (!path.startsWith('/')) return path
  const base = editionBase(pathname)
  return base && !path.startsWith(`${base}/`) && path !== base ? `${base}${path}` : path
}

export function editionStorageKey(key: string, pathname = window.location.pathname): string {
  return `farmtact:${editionFromPath(pathname) || 'global'}:${key}`
}

export function editionHome(edition = editionFromPath()): string {
  return edition ? `/${edition}/` : '/'
}
