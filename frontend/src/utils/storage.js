// localStorage puede no estar disponible (modo privado, política del navegador).
export const leer = (clave) => {
  try {
    return localStorage.getItem(clave)
  } catch {
    return null
  }
}
export const guardar = (clave, valor) => {
  try {
    localStorage.setItem(clave, valor)
  } catch {
    /* sin almacenamiento: la preferencia dura solo esta sesión */
  }
}
export const borrar = (clave) => {
  try {
    localStorage.removeItem(clave)
  } catch {
    /* nada que borrar */
  }
}
