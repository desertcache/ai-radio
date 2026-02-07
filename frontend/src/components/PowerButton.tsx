interface Props {
  powered: boolean
  onToggle: () => void
}

export function PowerButton({ powered, onToggle }: Props) {
  return (
    <button
      onClick={onToggle}
      className="relative w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300"
      style={{
        background: 'rgba(255,255,255,0.05)',
        border: '1px solid rgba(255,255,255,0.1)',
        boxShadow: powered ? '0 0 16px rgba(124,92,255,0.3)' : 'none',
      }}
      title={powered ? 'Turn off' : 'Turn on'}
    >
      {/* Power icon */}
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke={powered ? '#7c5cff' : 'rgba(255,255,255,0.3)'}
        strokeWidth="2.5"
        strokeLinecap="round"
        style={{
          filter: powered ? 'drop-shadow(0 0 4px #7c5cff)' : 'none',
          transition: 'all 0.3s',
        }}
      >
        <path d="M18.36 6.64a9 9 0 1 1-12.73 0" />
        <line x1="12" y1="2" x2="12" y2="12" />
      </svg>
    </button>
  )
}
