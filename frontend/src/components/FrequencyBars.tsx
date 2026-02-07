import { useRef, useEffect } from 'react'
import LiquidGlass from 'liquid-glass-react'
import { useGlassContainer } from '../context/GlassContext'
import { glassCard } from '../utils/glassPresets'

interface Props {
  audioDataRef: React.RefObject<{ amplitude: number; bands: number[] }>
  powered: boolean
}

export function FrequencyBars({ audioDataRef, powered }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const smoothedBandsRef = useRef<number[]>(new Array(16).fill(0))
  const peakBandsRef = useRef<number[]>(new Array(16).fill(0))
  const peakDecayRef = useRef<number[]>(new Array(16).fill(0))
  const container = useGlassContainer()

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animId: number

    const draw = () => {
      const w = canvas.width
      const h = canvas.height
      const bands = powered ? (audioDataRef.current?.bands ?? []) : []
      const numBands = 16
      const gap = 3
      const barWidth = (w - gap * (numBands + 1)) / numBands
      const maxBarHeight = h - 10

      // Clear
      ctx.clearRect(0, 0, w, h)

      // Semi-transparent bg so glass shows through
      ctx.fillStyle = 'rgba(0,0,0,0.2)'
      ctx.fillRect(0, 0, w, h)

      for (let i = 0; i < numBands; i++) {
        const target = bands[i] ?? 0
        const smoothed = smoothedBandsRef.current

        // Smooth rise fast, fall slow
        if (target > smoothed[i]) {
          smoothed[i] += (target - smoothed[i]) * 0.4
        } else {
          smoothed[i] += (target - smoothed[i]) * 0.1
        }

        // Peak hold
        if (smoothed[i] > peakBandsRef.current[i]) {
          peakBandsRef.current[i] = smoothed[i]
          peakDecayRef.current[i] = 0
        } else {
          peakDecayRef.current[i]++
          if (peakDecayRef.current[i] > 20) {
            peakBandsRef.current[i] *= 0.97
          }
        }

        const barHeight = smoothed[i] * maxBarHeight
        const x = gap + i * (barWidth + gap)
        const y = h - barHeight

        // Bar gradient: blue -> purple -> violet -> pink
        const grad = ctx.createLinearGradient(x, h, x, h - maxBarHeight)
        grad.addColorStop(0, '#5eadff')    // Blue
        grad.addColorStop(0.4, '#7c5cff')  // Purple
        grad.addColorStop(0.7, '#a855f7')  // Violet
        grad.addColorStop(1, '#ff4d6a')    // Pink-red

        ctx.fillStyle = grad
        ctx.fillRect(x, y, barWidth, barHeight)

        // Glow effect on loud bars
        if (smoothed[i] > 0.5) {
          ctx.shadowColor = '#7c5cff'
          ctx.shadowBlur = smoothed[i] * 10
          ctx.fillRect(x, y, barWidth, barHeight)
          ctx.shadowBlur = 0
        }

        // Peak dot
        const peakY = h - peakBandsRef.current[i] * maxBarHeight
        if (peakBandsRef.current[i] > 0.01) {
          ctx.fillStyle = '#ffffff'
          ctx.globalAlpha = 0.8
          ctx.fillRect(x, peakY - 2, barWidth, 2)
          ctx.globalAlpha = 1
        }
      }

      animId = requestAnimationFrame(draw)
    }

    draw()
    return () => cancelAnimationFrame(animId)
  }, [audioDataRef, powered])

  return (
    <LiquidGlass {...glassCard} mouseContainer={container ?? undefined} padding="0">
      <canvas
        ref={canvasRef}
        width={640}
        height={80}
        className="w-full h-auto block"
      />
    </LiquidGlass>
  )
}
