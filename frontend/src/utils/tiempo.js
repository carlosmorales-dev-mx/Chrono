// Si el backend manda fechas sin zona horaria y se ven corridas varias horas,
// este es el ÚNICO lugar que hay que ajustar (por ejemplo, tratarlas como UTC).
export function parseFecha(valor) {
  return new Date(valor).getTime()
}
