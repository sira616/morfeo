import { useEffect, useRef, type ReactNode } from 'react'
import { X } from 'lucide-react'

type ModalProps = {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
}

/**
 * Ventana modal sobre `<dialog>` nativo.
 *
 * Se usa el elemento del navegador en vez de un `div` con `position: fixed` porque
 * `showModal()` trae gratis lo que casi nunca se implementa bien a mano: el foco
 * atrapado dentro, cerrar con Escape, el resto de la página marcada como inerte para
 * los lectores de pantalla y el backdrop.
 */
export function Modal({ open, title, onClose, children }: ModalProps) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return

    // jsdom no implementa showModal, y algunos navegadores viejos tampoco. Con el
    // respaldo, ahí se abre como un diálogo normal: se pierden el backdrop y la
    // trampa de foco, pero se ve y se puede cerrar, que es lo importante.
    if (open && !dialog.open) {
      if (typeof dialog.showModal === 'function') dialog.showModal()
      else dialog.open = true
    }
    if (!open && dialog.open) {
      if (typeof dialog.close === 'function') dialog.close()
      else dialog.open = false
    }
  }, [open])

  return (
    <dialog
      ref={ref}
      // Escape dispara `cancel`, y cerrar el dialog sin avisar dejaría el estado de
      // React creyendo que sigue abierto.
      onCancel={(e) => {
        e.preventDefault()
        onClose()
      }}
      onClose={onClose}
      // Clic en el backdrop: el propio dialog es el objetivo cuando se pulsa fuera.
      onClick={(e) => {
        if (e.target === ref.current) onClose()
      }}
      aria-label={title}
      className="m-auto w-[min(34rem,92vw)] rounded-2xl p-0 text-ink backdrop:bg-black/60"
      style={{
        background: 'linear-gradient(160deg, var(--mf-surf-2), var(--mf-surf-1))',
        border: '1px solid var(--mf-line)',
        boxShadow: 'var(--mf-shadow-md)',
      }}
    >
      <div className="flex items-start justify-between gap-4 p-4 pb-0">
        <h2 className="text-headline-sm font-bold">{title}</h2>
        <button
          type="button"
          onClick={onClose}
          aria-label="Cerrar"
          className="grid min-h-touch min-w-touch place-items-center rounded-md opacity-70 hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo"
        >
          <X aria-hidden size={20} />
        </button>
      </div>
      <div className="max-h-[70vh] overflow-y-auto p-4 pt-2">{children}</div>
    </dialog>
  )
}
