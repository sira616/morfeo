import type { ReactNode } from 'react'
import { Moon } from 'lucide-react'
import { cn } from '@/lib/utils'

type ChatBubbleProps = {
  role: 'user' | 'assistant'
  children: ReactNode
  streaming?: boolean
  className?: string
}

function AssistantAvatar() {
  return (
    <span
      className="grid h-9 w-9 shrink-0 place-items-center self-end rounded-full"
      style={{
        background: 'linear-gradient(145deg, var(--mf-surf-2), var(--mf-surf-1))',
        border: '1px solid var(--mf-line)',
      }}
      aria-hidden
    >
      <Moon size={18} />
    </span>
  )
}

export function ChatBubble({ role, children, streaming, className }: ChatBubbleProps) {
  const isUser = role === 'user'

  return (
    <div className={cn('flex items-end gap-2', isUser && 'flex-row-reverse', className)}>
      {isUser ? null : <AssistantAvatar />}
      <div
        className={cn(
          'max-w-[80%] rounded-[18px] px-4 py-2 text-body-sm',
          isUser ? 'rounded-br-sm' : 'rounded-bl-sm',
        )}
        style={{
          background: isUser ? 'var(--mf-surf-3)' : 'var(--mf-surf-1)',
          border: '1px solid var(--mf-line)',
        }}
      >
        {children}
        {streaming ? (
          <span className="ml-1 inline-block animate-pulse" aria-label="escribiendo">
            …
          </span>
        ) : null}
      </div>
    </div>
  )
}
