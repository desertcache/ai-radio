import { useRef, useEffect } from 'react'
import LiquidGlass from 'liquid-glass-react'
import { useGlassContainer } from '../context/GlassContext'
import { glassCard } from '../utils/glassPresets'

interface Props {
  audioDataRef: React.RefObject<{ amplitude: number; bands: number[] }>
  channel: 'left' | 'right'
  powered: boolean
}

export function VUMeter({ audioDataRef, channel, powered }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const needleAngleRef = useRef(-45)
  const peakRef = useRef(0)
  const peakDecayRef = useRef(0)
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
      const cx = w / 2
      const cy = h * 0.85

      // Get amplitude
      const targetAmplitude = powered ? (audioDataRef.current?.amplitude ?? 0) : 0

      // Smooth needle movement (lerp)
      const targetAngle = -45 + targetAmplitude * 90 // -45 to +45 degrees
      needleAngleRef.current += (targetAngle - needleAngleRef.current) * 0.15

      // Peak hold
      if (targetAmplitude > peakRef.current) {
        peakRef.current = targetAmplitude
        peakDecayRef.current = 0
      } else {
        peakDecayRef.current += 1
        if (peakDecayRef.current > 30) { // Hold for ~1s at 30fps
          peakRef.current *= 0.98
        }
      }

      // Clear
      ctx.clearRect(0, 0, w, h)

      // Semi-transparent bg so glass shows through
      ctx.fillStyle = 'rgba(0,0,0,0.2)'
      ctx.fillRect(0, 0, w, h)

      // Draw scale arc
      const radius = h * 0.6
      const startAngle = Math.PI + Math.PI / 4 // -45 deg from bottom
      const endAngle = 2 * Math.PI - Math.PI / 4 // +45 deg from bottom

      // Scale markings
      for (let i = 0; i <= 10; i++) {
        const frac = i / 10
        const angle = startAngle + frac * (endAngle - startAngle)
        const innerR = radius * 0.8
        const outerR = radius * 0.95

        const x1 = cx + Math.cos(angle) * innerR
        const y1 = cy + Math.sin(angle) * innerR
        const x2 = cx + Math.cos(angle) * outerR
        const y2 = cy + Math.sin(angle) * outerR

        ctx.strokeStyle = frac > 0.7 ? '#ff4d6a' : 'rgba(255,255,255,0.3)'
        ctx.lineWidth = i % 2 === 0 ? 2 : 1
        ctx.globalAlpha = 0.6
        ctx.beginPath()
        ctx.moveTo(x1, y1)
        ctx.lineTo(x2, y2)
        ctx.stroke()

        // Labels at major marks
        if (i % 2 === 0) {
          const labelR = radius * 0.7
          const lx = cx + Math.cos(angle) * labelR
          const ly = cy + Math.sin(angle) * labelR
          ctx.fillStyle = frac > 0.7 ? '#ff4d6a' : 'rgba(255,255,255,0.3)'
          ctx.globalAlpha = 0.5
          ctx.font = '9px Inter, sans-serif'
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillText(`${i * 10}`, lx, ly)
        }
      }
      ctx.globalAlpha = 1

      // Peak indicator
      const peakAngle = startAngle + peakRef.current * (endAngle - startAngle)
      const peakR = radius * 0.88
      ctx.fillStyle = '#ff4d6a'
      ctx.globalAlpha = 0.7
      ctx.beginPath()
      ctx.arc(cx + Math.cos(peakAngle) * peakR, cy + Math.sin(peakAngle) * peakR, 2, 0, Math.PI * 2)
      ctx.fill()
      ctx.globalAlpha = 1

      // Needle
      const needleRad = (needleAngleRef.current * Math.PI) / 180
      const needleAngle = Math.PI * 1.5 + needleRad // Convert to canvas angle
      const needleLen = radius * 0.9

      ctx.strokeStyle = '#7c5cff'
      ctx.lineWidth = 1.5
      ctx.shadowColor = '#7c5cff'
      ctx.shadowBlur = powered ? 6 : 0
      ctx.beginPath()
      ctx.moveTo(cx, cy)
      ctx.lineTo(
        cx + Math.cos(needleAngle) * needleLen,
        cy + Math.sin(needleAngle) * needleLen,
      )
      ctx.stroke()
      ctx.shadowBlur = 0

      // Needle pivot
      ctx.fillStyle = 'rgba(255,255,255,0.6)'
      ctx.beginPath()
      ctx.arc(cx, cy, 4, 0, Math.PI * 2)
      ctx.fill()

      // Label
      ctx.fillStyle = 'rgba(255,255,255,0.3)'
      ctx.globalAlpha = 0.4
      ctx.font = 'bold 10px Inter, sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(channel === 'left' ? 'L' : 'R', cx, h * 0.35)
      ctx.globalAlpha = 1

      animId = requestAnimationFrame(draw)
    }

    draw()
    return () => cancelAnimationFrame(animId)
  }, [audioDataRef, channel, powered])

  return (
    <LiquidGlass {...glassCard} mouseContainer={container ?? undefined} padding="0">
      <canvas
        ref={canvasRef}
        width={160}
        height={110}
        className="w-full h-auto block"
      />
    </LiquidGlass>
  )
}
