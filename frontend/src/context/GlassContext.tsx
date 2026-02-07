import { createContext, useContext } from 'react'
import type { RefObject } from 'react'

export const GlassContext = createContext<RefObject<HTMLDivElement | null> | null>(null)

export function useGlassContainer() {
  return useContext(GlassContext)
}
