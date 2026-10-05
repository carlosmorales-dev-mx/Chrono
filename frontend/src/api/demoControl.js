import { ref } from 'vue'
import { DEMO_ESCENARIO } from '../config'

// Escenario activo del modo demo. Es reactivo para que el aviso superior muestre cuál está seleccionado.
//   lento -> DeepSeek responde lento · caida -> además OpenAI no responde · ok -> todo operativo
export const escenarioDemo = ref(DEMO_ESCENARIO)
