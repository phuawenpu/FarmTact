import { editionStorageKey } from './edition'
/** Local drafts are never submitted records. Bound storage to the newest 24 contexts. */
export function workspaceDrafts<T>(namespace:string):Map<string,T> {
 const key=editionStorageKey(`v22-drafts:${namespace}`)
 const map=new Map<string,T>()
 try {const rows=JSON.parse(localStorage.getItem(key)||'[]');if(Array.isArray(rows))for(const row of rows.slice(-24))if(Array.isArray(row)&&typeof row[0]==='string')map.set(row[0],row[1])}catch{}
 const persist=()=>{try{localStorage.setItem(key,JSON.stringify([...map.entries()].slice(-24)))}catch{/* Storage may be unavailable; the in-memory draft remains. */}}
 const set=map.set.bind(map),remove=map.delete.bind(map)
 map.set=(k,v)=>{set(k,v);persist();return map}
 map.delete=k=>{const result=remove(k);persist();return result}
 return map
}
