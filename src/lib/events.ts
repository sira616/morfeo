/** Eventos SSE del check-in. Los emite `app/api/checkin.py` en el backend. */
export type CheckinEvent =
  | { node: 'context'; data: { turn: number; known: string[] } }
  | { node: 'reply'; data: { chunk: string } }
  | { node: 'extracted'; data: { fields: Record<string, string> } }
