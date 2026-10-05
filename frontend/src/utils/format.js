/** 842 -> { valor: '842', unidad: 'ms' } ; 2425 -> { valor: '2.4', unidad: 's' } */
export function partesMs(n) {
  if (n === null || n === undefined || !Number.isFinite(n)) return null
  return n >= 1000 ? { valor: (n / 1000).toFixed(1), unidad: 's' } : { valor: String(Math.round(n)), unidad: 'ms' }
}

export function textoMs(n) {
  const p = partesMs(n)
  return p ? `${p.valor} ${p.unidad}` : '—'
}

export function porcentaje(v) {
  return `${v >= 10 ? Math.round(v) : v.toFixed(1)} %`
}
