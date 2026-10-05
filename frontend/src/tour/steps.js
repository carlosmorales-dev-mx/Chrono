/**
 * Los pasos del tutorial.
 *
 * Cada paso dice QUÉ resaltar (`target`: selector, lista de selectores o función) y QUÉ demostrar (`run`),
 * usando las herramientas `X` del motor: mover el cursor, hacer clic, barrer una gráfica, escribir…
 * `base` indica en qué pantalla arranca el paso ('panel' por defecto). `n` es el número del texto en los
 * idiomas (tour.sN.t / tour.sN.d); `soloDemo` marca los pasos que necesitan datos simulados.
 */
const filaProblema = () =>
  document.querySelector('#c-svc .svc.degraded, #c-svc .svc.down') || document.querySelector('#c-svc .svc')
const enFila = (sel) => () => {
  const f = filaProblema()
  return f ? f.querySelector(sel) : null
}

export const PASOS = [
  { n: 1, target: '.band', cursor: false, run: async (X) => { await X.wait(600) } },

  { n: 2, target: '#strip', run: async (X) => { await X.sweep('#strip', 0.03, 0.97, 2800, '#strip .seg') } },

  {
    n: 3,
    target: filaProblema,
    run: async (X) => {
      await X.to(enFila('[data-k="sub"]'), { fx: 0.3 })
      await X.wait(1100)
      await X.to(enFila('.tape'))
      await X.wait(900)
    },
  },

  {
    n: 4,
    target: filaProblema,
    run: async (X) => {
      await X.click(enFila('.svc-main'))
      await X.wait(700)
      await X.chartSweep(() => {
        const f = filaProblema()
        return f ? f.querySelector('.chart') : null
      }, 2600)
    },
  },

  {
    n: 5,
    target: filaProblema,
    run: async (X) => {
      X.mark(filaProblema(), 'sim-hover')
      await X.to(enFila('[data-act="pin"]'))
      await X.wait(800)
      await X.to(enFila('[data-act="edit"]'))
      await X.wait(800)
      await X.to(enFila('[data-act="del"]'))
      await X.wait(1000)
    },
  },

  {
    n: 6,
    target: '#c-svc .card-h',
    run: async (X) => {
      await X.click('[data-filter="issues"]')
      await X.wait(1500)
      await X.click('[data-filter="pinned"]')
      await X.wait(1500)
      await X.click('[data-filter="all"]')
      await X.wait(500)
    },
  },

  { n: 7, target: '#c-act', run: async (X) => { await X.sweep('#c-act .fleet', 0.02, 0.98, 3000, '#c-act .fleet i') } },

  {
    n: 8,
    target: '#c-inc',
    run: async (X) => {
      await X.to('#c-inc .link')
      await X.wait(300)
      await X.press()
      await X.wait(700)
    },
  },

  {
    n: 9,
    target: () => (document.getElementById('v-inc') ? ['#v-inc .band', '.inc-top'] : '#nav'),
    run: async (X) => {
      await X.click('#nav [data-view="inc"]')
      await X.wait(800)
      await X.to('#i-feat .feat-name', { fx: 0.4 })
      await X.wait(900)
      await X.chartSweep(() => document.querySelector('#i-feat .chart'), 2200)
      await X.sweep('#i-sum', 0.1, 0.9, 1800, '#i-sum .dato')
    },
  },

  {
    n: 10,
    base: 'inc',
    target: '#v-inc .controls',
    run: async (X) => {
      await X.click('[data-ifilter="type:down"]')
      await X.wait(1300)
      await X.click('[data-ifilter="range:24h"]')
      await X.wait(1500)
      await X.click('[data-ifilter="type:all"]')
      await X.wait(500)
      await X.click('[data-ifilter="range:30d"]')
      await X.wait(500)
    },
  },

  {
    n: 11,
    base: 'inc',
    target: () => document.querySelector('#i-list .irow'),
    run: async (X) => {
      await X.click(() => document.querySelector('#i-list .irow-main'))
      await X.wait(700)
      await X.chartSweep(() => document.querySelector('#i-list .chart'), 2400)
    },
  },

  {
    n: 12,
    soloDemo: true,
    target: ['.top', '.band'],
    run: async (X) => {
      await X.wait(700)
      await X.scenario('caida')
      await X.wait(1000)
      await X.to('.band h1', { fx: 0.3 })
      await X.wait(1400)
      await X.to('#wm-o')
      await X.wait(1300)
      await X.to('#nav .n')
      await X.wait(1500)
      await X.scenario('ok')
      await X.wait(2000)
      await X.scenario('lento')
      await X.wait(700)
    },
  },

  {
    n: 13,
    target: () => document.querySelector('dialog[open]') || '[data-act="add"]',
    run: async (X) => {
      X.busy(true)
      X.alLimpiar(() => X.busy(false))
      await X.click('[data-act="add"]')
      await X.wait(500)
      X.alFrente()
      await X.to('#f-name')
      await X.type('#f-name', 'Mi API')
      await X.wait(250)
      await X.to('#f-url')
      await X.type('#f-url', 'miapi.dev')
      await X.wait(1000)
      await X.click('[data-dlg="cancel"]')
      await X.wait(400)
      X.busy(false)
    },
  },

  {
    n: 14,
    target: '#tools',
    run: async (X) => {
      await X.click('#tools [data-act="theme"]')
      await X.wait(1600)
      await X.click('#tools [data-act="theme"]')
      await X.wait(900)
      await X.click('#tools [data-lang="en"]')
      await X.wait(1600)
      await X.click('#tools [data-lang="es"]')
      await X.wait(600)
    },
  },

  { n: 15, target: null, cursor: false, final: true, run: async (X) => { await X.wait(300) } },
]
