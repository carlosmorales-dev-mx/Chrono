/**
 * Motor del tutorial interactivo.
 *
 * Un recorrido guiado: un foco que se mueve, una tarjeta explicativa y un cursor animado que ejecuta
 * las acciones DE VERDAD sobre la interfaz (clics, escritura, barridos sobre las gráficas).
 * Cada paso arranca desde un estado conocido (`baseline`), así que se puede ir adelante, atrás o repetir
 * sin que nada quede a medias.
 *
 * Es JavaScript puro: todo lo que necesita de la app (estado reactivo, navegación, tema…) llega por
 * `deps`, y los elementos del DOM por `registrar()`. Eso lo mantiene fácil de leer y de probar.
 */
const CANCEL = { cancelado: true }

const nextFrame = () => new Promise((r) => requestAnimationFrame(() => r()))
const clamp = (v, a, b) => Math.max(a, Math.min(b, v))

/**
 * @param {object} deps
 * @param {object} deps.estado        objeto reactivo { activo, idx, total, ocupado, pct, n, final }
 * @param {Array}  deps.pasos         lista de pasos (ver steps.js)
 * @param {Function} deps.baseline    async (vista) => deja la app en un estado limpio y conocido
 * @param {Function} deps.snapshot    () => foto del estado actual de la app
 * @param {Function} deps.restaurar   async (foto) => devuelve la app a como estaba
 * @param {Function|null} deps.escenario  async (nombre) => cambia el escenario de la demo (null fuera de la demo)
 * @param {Function} deps.alCambiarFoco   () => se llama tras renderizar la tarjeta (para enfocar el botón)
 * @param {Function} deps.esperarDom  async () => espera a que Vue pinte
 */
export function crearMotor(deps) {
  const { estado, pasos, baseline, snapshot, restaurar, escenario, alCambiarFoco, esperarDom } = deps

  const T = {
    token: 0,
    snap: null,
    speed: 1,
    cx: 0,
    cy: 0,
    lastKey: '',
    size: '',
    placedRect: null,
    cleanups: [],
    prevPct: 0,
  }
  let els = null // { raiz, foco, tarjeta, cursor, ondas }

  const reducido = () => !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches)

  const alLimpiar = (fn) => T.cleanups.push(fn)
  function limpiar() {
    T.cleanups.splice(0).forEach((fn) => {
      try {
        fn()
      } catch {
        /* el elemento ya no existe */
      }
    })
  }
  function ocupado(v) {
    estado.ocupado = v
  }

  /* ------------------------------------------------------------------ cursor */
  function moverCursor(x, y, ms) {
    els.cursor.classList.add('on')
    els.cursor.style.transitionDuration = ms + 'ms'
    els.cursor.style.transform = `translate(${x}px, ${y}px)`
    T.cx = x
    T.cy = y
  }
  function onda(x, y) {
    const r = document.createElement('span')
    r.className = 'rip'
    r.style.left = x + 'px'
    r.style.top = y + 'px'
    els.ondas.appendChild(r)
    setTimeout(() => r.remove(), 750)
  }

  // El popover del tutorial queda por debajo de un <dialog> modal que se abra después; se vuelve a mostrar al frente.
  function alFrente() {
    try {
      els.raiz.hidePopover()
      els.raiz.showPopover()
    } catch {
      /* sin API popover: no hay nada que reordenar */
    }
  }

  /* Herramientas que usa cada demostración. Si el paso cambia mientras corre, lanzan CANCEL. */
  function crearX(tok) {
    const viva = () => {
      if (tok !== T.token || !estado.activo) throw CANCEL
    }
    const wait = async (ms) => {
      await new Promise((r) => setTimeout(r, ms * T.speed))
      viva()
    }
    const find = (s) => (typeof s === 'function' ? s() : typeof s === 'string' ? document.querySelector(s) : s)

    async function to(sel, o) {
      o = o || {}
      viva()
      const e = find(sel)
      if (!e) return null
      let r = e.getBoundingClientRect()
      if (r.width === 0 && r.height === 0) return null
      if (e.scrollIntoView) {
        e.scrollIntoView({ block: 'nearest', inline: 'nearest' })
        r = e.getBoundingClientRect()
      }
      const x = r.left + r.width * (o.fx == null ? 0.5 : o.fx)
      const y = r.top + r.height * (o.fy == null ? 0.5 : o.fy)
      const ms = o.dur || Math.round(Math.min(1100, 360 + Math.hypot(x - T.cx, y - T.cy) * 0.9))
      moverCursor(x, y, ms * T.speed)
      await wait(ms + 80)
      return e
    }
    async function press() {
      els.cursor.classList.add('press')
      onda(T.cx, T.cy)
      await wait(150)
      els.cursor.classList.remove('press')
    }
    async function click(sel) {
      const e = await to(sel)
      if (!e) return null
      await press()
      e.click()
      await wait(260)
      return e
    }
    function mark(e, cls) {
      if (!e) return
      e.classList.add(cls)
      alLimpiar(() => e.classList.remove(cls))
    }
    // Marca como "hover" el elemento que queda bajo el cursor mientras este se desplaza.
    function track(itemsSel) {
      const id = setInterval(() => {
        const c = els.cursor.getBoundingClientRect()
        document.querySelectorAll(itemsSel).forEach((it) => {
          const r = it.getBoundingClientRect()
          it.classList.toggle('sim-hover', c.left >= r.left - 1 && c.left <= r.right + 1)
        })
      }, 40)
      const stop = () => {
        clearInterval(id)
        document.querySelectorAll(itemsSel).forEach((it) => it.classList.remove('sim-hover'))
      }
      alLimpiar(stop)
      return stop
    }
    async function sweep(sel, fx0, fx1, ms, itemsSel) {
      await to(sel, { fx: fx0 })
      const stop = track(itemsSel)
      try {
        await to(sel, { fx: fx1, dur: ms })
      } finally {
        stop()
      }
    }
    // Recorre una gráfica enviándole los mismos eventos que mandaría un ratón real.
    async function chartSweep(sel, ms) {
      viva()
      const ch = find(sel)
      if (!ch) return
      await to(ch, { fx: 0.05 })
      const id = setInterval(() => {
        const c = els.cursor.getBoundingClientRect()
        ch.dispatchEvent(new MouseEvent('pointermove', { bubbles: true, clientX: c.left, clientY: c.top }))
      }, 35)
      const stop = () => {
        clearInterval(id)
        ch.dispatchEvent(new MouseEvent('pointerout', { bubbles: true }))
      }
      alLimpiar(stop)
      try {
        await to(ch, { fx: 0.95, dur: ms })
        await wait(500)
      } finally {
        stop()
      }
    }
    async function type(sel, text) {
      const e = find(sel)
      if (!e) return
      e.focus()
      e.value = ''
      e.dispatchEvent(new Event('input', { bubbles: true }))
      for (const ch of text) {
        e.value += ch
        e.dispatchEvent(new Event('input', { bubbles: true })) // para que v-model se entere
        await wait(80 + Math.random() * 50)
      }
    }
    async function scenario(nombre) {
      if (!escenario) return
      await escenario(nombre)
      viva()
    }
    return { wait, to, press, click, mark, sweep, chartSweep, type, scenario, find, busy: ocupado, alLimpiar, alFrente }
  }

  /* ------------------------------------------------------- foco y tarjeta */
  function resolverObjetivo(paso) {
    const tg = typeof paso.target === 'function' ? paso.target() : paso.target
    if (!tg) return { rect: null, els: [], key: 'none' }
    const lista = Array.isArray(tg) ? tg : [tg]
    const encontrados = lista.map((x) => (typeof x === 'string' ? document.querySelector(x) : x)).filter(Boolean)
    const rs = encontrados.map((e) => e.getBoundingClientRect()).filter((r) => r.width > 0 && r.height > 0)
    if (!rs.length) return { rect: null, els: encontrados, key: 'oculto' }
    const left = Math.min(...rs.map((r) => r.left))
    const top = Math.min(...rs.map((r) => r.top))
    const right = Math.max(...rs.map((r) => r.right))
    const bottom = Math.max(...rs.map((r) => r.bottom))
    const key = encontrados.map((e) => e.id || e.getAttribute('data-id') || e.tagName + '.' + String(e.className)).join('|')
    return { rect: { left, top, right, bottom, width: right - left, height: bottom - top }, els: encontrados, key }
  }

  function colocarTarjeta(rect) {
    const tarjeta = els.tarjeta
    const cw = tarjeta.offsetWidth
    const ch = tarjeta.offsetHeight
    const vw = window.innerWidth
    const vh = window.innerHeight
    const m = 14
    const gap = 14
    let left
    let top
    if (!rect) {
      left = (vw - cw) / 2
      top = (vh - ch) / 2
    } else if (vh - rect.bottom - m >= ch + gap) {
      top = rect.bottom + gap
      left = rect.left + rect.width / 2 - cw / 2
    } else if (rect.top - m >= ch + gap) {
      top = rect.top - ch - gap
      left = rect.left + rect.width / 2 - cw / 2
    } else if (vw - rect.right - m >= cw + gap) {
      left = rect.right + gap
      top = rect.top + rect.height / 2 - ch / 2
    } else if (rect.left - m >= cw + gap) {
      left = rect.left - cw - gap
      top = rect.top + rect.height / 2 - ch / 2
    } else {
      left = vw - cw - 24
      top = vh - ch - 24
    }
    tarjeta.style.left = clamp(left, m, Math.max(m, vw - cw - m)) + 'px'
    tarjeta.style.top = clamp(top, m, Math.max(m, vh - ch - m)) + 'px'
  }

  // Cada fotograma: el foco sigue al elemento aunque cambie de tamaño o de lugar (p. ej. al abrirse una fila).
  function bucle() {
    if (!estado.activo) return
    const paso = pasos[estado.idx]
    if (paso) {
      const t = resolverObjetivo(paso)
      const pad = 8
      const foco = els.foco
      if (t.rect) {
        foco.style.left = Math.round(t.rect.left - pad) + 'px'
        foco.style.top = Math.round(t.rect.top - pad) + 'px'
        foco.style.width = Math.round(t.rect.width + pad * 2) + 'px'
        foco.style.height = Math.round(t.rect.height + pad * 2) + 'px'
        foco.style.opacity = '1'
      } else if (t.key === 'none') {
        foco.style.left = Math.round(window.innerWidth / 2) + 'px'
        foco.style.top = Math.round(window.innerHeight / 2) + 'px'
        foco.style.width = '0px'
        foco.style.height = '0px'
        foco.style.opacity = '0'
      } // key === 'oculto': el destino está cambiando de pantalla; se deja el foco donde estaba
      const tam = window.innerWidth + 'x' + window.innerHeight
      const p0 = T.placedRect
      const movido = !!(t.rect && p0 && (Math.abs(t.rect.top - p0.top) > 24 || Math.abs(t.rect.bottom - p0.bottom) > 24 || Math.abs(t.rect.left - p0.left) > 24 || Math.abs(t.rect.right - p0.right) > 24))
      if (t.key !== 'oculto' && (t.key !== T.lastKey || tam !== T.size || movido)) {
        T.lastKey = t.key
        T.size = tam
        T.placedRect = t.rect
        colocarTarjeta(
          t.rect
            ? { left: t.rect.left - pad, top: t.rect.top - pad, right: t.rect.right + pad, bottom: t.rect.bottom + pad, width: t.rect.width + pad * 2, height: t.rect.height + pad * 2 }
            : null
        )
      }
    }
    requestAnimationFrame(bucle)
  }

  /* --------------------------------------------------------- ciclo de vida */
  async function mostrar(i) {
    limpiar()
    T.token++
    const tok = T.token
    const paso = pasos[i]
    estado.idx = i
    estado.n = paso.n
    estado.final = !!paso.final
    ocupado(false)
    try {
      await baseline(paso.base || 'panel')
    } catch (err) {
      console.warn('tutorial (estado inicial):', err)
    }
    if (tok !== T.token) return
    if (paso.cursor === false) els.cursor.classList.remove('on')
    // barra de progreso: parte del valor anterior y se anima hasta el nuevo
    estado.pct = T.prevPct
    T.prevPct = Math.round(((i + 1) / pasos.length) * 100)
    await esperarDom()
    requestAnimationFrame(() => {
      if (tok === T.token) estado.pct = T.prevPct
    })
    alCambiarFoco()
    els.foco.classList.remove('pulso')
    void els.foco.offsetWidth
    els.foco.classList.add('pulso')
    T.lastKey = ''
    T.placedRect = null
    await nextFrame()
    await nextFrame()
    if (tok !== T.token) return
    const t = resolverObjetivo(paso)
    if (t.els[0] && t.els[0].scrollIntoView) t.els[0].scrollIntoView({ block: 'nearest' })
    try {
      await paso.run(crearX(tok))
    } catch (err) {
      if (err !== CANCEL) console.warn('tutorial:', err)
    } finally {
      if (tok === T.token) ocupado(false)
    }
  }

  function ir(i) {
    if (i < 0 || i >= pasos.length) return
    mostrar(i)
  }

  function alTeclear(e) {
    if (!estado.activo || estado.ocupado) return
    if (e.key === 'Escape') {
      e.preventDefault()
      cerrar()
    } else if (e.key === 'ArrowRight') {
      e.preventDefault()
      ir(estado.idx + 1)
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault()
      ir(estado.idx - 1)
    } else if (e.key === 'Tab') {
      const f = Array.from(els.tarjeta.querySelectorAll('button'))
      if (!f.length) return
      const a = document.activeElement
      if (!els.tarjeta.contains(a)) {
        e.preventDefault()
        f[0].focus()
      } else if (e.shiftKey && a === f[0]) {
        e.preventDefault()
        f[f.length - 1].focus()
      } else if (!e.shiftKey && a === f[f.length - 1]) {
        e.preventDefault()
        f[0].focus()
      }
    }
  }

  function registrar(elementos) {
    els = elementos
  }

  function iniciar() {
    if (estado.activo || !els) return
    estado.activo = true
    estado.total = pasos.length
    T.snap = snapshot()
    T.speed = reducido() ? 0.5 : 1
    T.prevPct = 0
    estado.pct = 0
    els.raiz.setAttribute('aria-hidden', 'false')
    try {
      els.raiz.showPopover()
    } catch {
      els.raiz.classList.add('open')
    }
    els.cursor.classList.remove('on')
    els.cursor.style.transitionDuration = '0ms'
    T.cx = window.innerWidth * 0.82
    T.cy = window.innerHeight * 0.9
    els.cursor.style.transform = `translate(${T.cx}px, ${T.cy}px)`
    document.addEventListener('keydown', alTeclear, true)
    requestAnimationFrame(bucle)
    mostrar(0)
  }

  async function cerrar() {
    if (!estado.activo) return
    T.token++
    limpiar()
    estado.activo = false
    ocupado(false)
    document.removeEventListener('keydown', alTeclear, true)
    try {
      els.raiz.hidePopover()
    } catch {
      /* ya cerrado */
    }
    els.raiz.classList.remove('open')
    els.raiz.setAttribute('aria-hidden', 'true')
    await restaurar(T.snap)
    const b = document.querySelector('[data-act="tour"]')
    if (b) b.focus({ preventScroll: true })
  }

  // Botones de la tarjeta (los pinta Vue; aquí solo se decide qué hace cada uno).
  function accion(a) {
    if (estado.ocupado) return
    if (a === 'next') ir(estado.idx + 1)
    else if (a === 'prev') ir(estado.idx - 1)
    else if (a === 'replay') ir(estado.idx)
    else if (a === 'again') ir(0)
    else if (a === 'try') {
      if (escenario) T.snap.escenario = 'caida'
      cerrar()
    } else if (a === 'skip' || a === 'close') cerrar()
  }

  return { registrar, iniciar, cerrar, accion }
}
