import { useRef, useEffect } from 'react'
import { Send } from 'lucide-react'
import './Composer.css'

interface ComposerProps {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  disabled?: boolean
  placeholder?: string
}

export function Composer({ value, onChange, onSubmit, disabled, placeholder }: ComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return

    textarea.style.height = 'auto'
    const newHeight = Math.min(textarea.scrollHeight, 140)
    textarea.style.height = `${newHeight}px`
  }, [value])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!disabled && value.trim()) {
        onSubmit()
      }
    }
  }

  return (
    <div className="composer">
      <div className="composer-inner">
        <textarea
          ref={textareaRef}
          className="composer-textarea"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || 'Ask a question…'}
          disabled={disabled}
          aria-label="Message input"
        />
        <button
          className="composer-send"
          onClick={onSubmit}
          disabled={disabled || !value.trim()}
          title="Send (Enter)"
        >
          <Send size={18} />
        </button>
      </div>
      <div className="composer-hint">
        <kbd>Enter</kbd> to send · <kbd>Shift</kbd> + <kbd>Enter</kbd> for newline
      </div>
    </div>
  )
}
