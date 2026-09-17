export type EditionId = `v${number}`
export const CURRENT_EDITION: EditionId = 'v18'

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
  // The public URL no longer exposes releases, but progress still belongs to an
  // immutable application generation. A future release changes this namespace.
  return `farmtact:${editionFromPath(pathname) || CURRENT_EDITION}:${key}`
}

export function editionHome(edition = editionFromPath()): string {
  return edition ? `/${edition}/` : '/'
}
