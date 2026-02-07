import { useRef, type ReactNode } from 'react'
import LiquidGlass from 'liquid-glass-react'
import { MeshBackground } from './MeshBackground'
import { GlassContext } from '../context/GlassContext'
import { glassPanel } from '../utils/glassPresets'

interface Props {
  children: ReactNode
  powered: boolean
}

export function RadioCabinet({ children, powered }: Props) {
  const viewportRef = useRef<HTMLDivElement>(null)

  return (
    <div ref={viewportRef} className="flex items-center justify-center min-h-screen p-8 relative">
      <MeshBackground />

      <GlassContext.Provider value={viewportRef}>
        <div className="relative w-full max-w-[720px] z-10">
          <LiquidGlass
            {...glassPanel}
            mouseContainer={viewportRef}
            padding="0"
          >
            {/* Accent glow line at top */}
            <div
              className="h-px transition-opacity duration-1000"
              style={{
                background: 'linear-gradient(90deg, transparent, var(--accent), transparent)',
                opacity: powered ? 0.7 : 0,
              }}
            />

            <div className="p-5 space-y-4">
              {children}
            </div>
          </LiquidGlass>

          {/* Bottom brand text */}
          <div className="text-center pt-3">
            <span
              className="text-[10px] tracking-[0.3em] uppercase"
              style={{ color: 'var(--text-muted)' }}
            >
              KPXL Nocturnal Radio
            </span>
          </div>
        </div>
      </GlassContext.Provider>
    </div>
  )
}
