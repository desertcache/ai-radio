export function MeshBackground() {
  return (
    <div className="mesh-bg">
      {/* Rotating conic gradient */}
      <div className="mesh-gradient" />

      {/* Floating orbs */}
      <div className="mesh-orb mesh-orb-1" />
      <div className="mesh-orb mesh-orb-2" />
      <div className="mesh-orb mesh-orb-3" />

      {/* Noise overlay */}
      <svg className="mesh-noise" width="100%" height="100%">
        <filter id="noise">
          <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch" />
        </filter>
        <rect width="100%" height="100%" filter="url(#noise)" opacity="0.03" />
      </svg>
    </div>
  )
}
