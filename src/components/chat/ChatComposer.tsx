import { useState, type FormEvent, type KeyboardEvent } from 'react'
import { Paperclip, Send } from 'lucide-react'
import { cn } from '@/lib/utils'

type ChatComposerProps = {
  onSend: (message: string) => void
  disabled?: boolean
  placeholder?: string
  className?: string
}

export function ChatComposer({
  onSend,
  disabled = false,
  placeholder = 'Escribe a Carlos…',
  className,
}: ChatComposerProps) {
  const [draft, setDraft] = useState('')

  function submit() {
    const text = draft.trim()
    if (!text || disabled) return
    onSend(text)
    setDraft('')
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    submit()
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <form
      className={cn('flex items-end gap-2.5 px-4 pb-3', className)}
      onSubmit={onSubmit}
    >
      <div
        className="flex min-h-[48px] flex-1 items-end gap-1 rounded-[16px] border border-[color:var(--mf-line-strong)] px-2.5 py-1.5"
        style={{
          background: 'linear-gradient(160deg, var(--mf-surf-2), var(--mf-surf-1))',
          boxShadow: 'var(--mf-shadow-md)',
        }}
      >
        <button
          type="button"
          aria-label="Adjuntar archivo"
          disabled={disabled}
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center text-ink-faint hover:text-ink disabled:opacity-50"
        >
          <Paperclip size={18} aria-hidden />
        </button>
        <textarea
          aria-label="Mensaje"
          rows={1}
          disabled={disabled}
          placeholder={placeholder}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          className="max-h-28 flex-1 resize-none bg-transparent py-2 text-[14.5px] text-ink placeholder:text-ink-faint focus:outline-none disabled:opacity-50"
          style={{ fontFamily: 'inherit' }}
        />
      </div>
      <button
        type="submit"
        aria-label="Enviar mensaje"
        disabled={disabled || !draft.trim()}
        className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-[14px] transition-transform active:scale-95 disabled:opacity-50"
        style={{
          color: 'var(--mf-on-brand)',
          background:
            'linear-gradient(145deg, var(--mf-brand-yellow), #e6c22e 45%, var(--mf-brand-green))',
          boxShadow: 'var(--mf-shadow-brand)',
        }}
      >
        <Send size={18} aria-hidden />
      </button>
    </form>
  )
}
