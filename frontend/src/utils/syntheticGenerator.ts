/**
 * SyntheticGenerator — Story 8.4
 * Generates synthetic test data from XSD field definitions with realistic Brazilian values.
 */

import type { XsdFieldDef } from '@/types/test-data.types'

export type SyntheticSize = 'small' | 'medium' | 'large'

/** Number of items to generate for array fields by size */
const ARRAY_SIZES: Record<SyntheticSize, number> = {
  small: 1,
  medium: 10,
  large: 100,
}

// ─── Brazilian value generators (no external dependency) ─────────────────────

const BR_FIRST_NAMES = [
  'João',
  'Maria',
  'Pedro',
  'Ana',
  'Carlos',
  'Fernanda',
  'Lucas',
  'Juliana',
  'Rafael',
  'Camila',
  'Bruno',
  'Beatriz',
  'Guilherme',
  'Larissa',
  'Marcos',
  'Patrícia',
  'Eduardo',
  'Vanessa',
  'Felipe',
  'Renata',
]

const BR_LAST_NAMES = [
  'Silva',
  'Santos',
  'Oliveira',
  'Souza',
  'Rodrigues',
  'Ferreira',
  'Alves',
  'Pereira',
  'Lima',
  'Gomes',
  'Costa',
  'Ribeiro',
  'Martins',
  'Carvalho',
  'Almeida',
  'Lopes',
  'Soares',
  'Fernandes',
  'Vieira',
  'Barbosa',
]

const BR_CITIES = [
  'São Paulo',
  'Rio de Janeiro',
  'Belo Horizonte',
  'Salvador',
  'Fortaleza',
  'Curitiba',
  'Manaus',
  'Recife',
  'Porto Alegre',
  'Belém',
]

const BR_STATES = ['SP', 'RJ', 'MG', 'BA', 'CE', 'PR', 'AM', 'PE', 'RS', 'PA']

const BR_STREETS = [
  'Rua das Flores',
  'Avenida Brasil',
  'Rua Sete de Setembro',
  'Avenida Paulista',
  'Rua Augusta',
  'Travessa das Acácias',
  'Rua Dom Pedro II',
  'Avenida Getúlio Vargas',
]

let _counter = 0

function nextInt(min: number, max: number): number {
  _counter = (_counter * 1664525 + 1013904223) & 0x7fffffff
  return (_counter % (max - min + 1)) + min
}

/** Reset counter for deterministic test output */
export function resetCounter(): void {
  _counter = 0
}

function pickFrom<T>(arr: T[]): T {
  return arr[nextInt(0, arr.length - 1)]!
}

// ─── CPF Generator ───────────────────────────────────────────────────────────

function calcCpfDigit(partial: number[]): number {
  const weight = partial.length + 1
  let sum = 0
  for (let i = 0; i < partial.length; i++) {
    sum += partial[i]! * (weight - i)
  }
  const rem = sum % 11
  return rem < 2 ? 0 : 11 - rem
}

export function generateCpf(): string {
  const digits: number[] = []
  for (let i = 0; i < 9; i++) digits.push(nextInt(0, 9))
  digits.push(calcCpfDigit(digits))
  digits.push(calcCpfDigit(digits))
  const d = digits
  return `${d[0]}${d[1]}${d[2]}.${d[3]}${d[4]}${d[5]}.${d[6]}${d[7]}${d[8]}-${d[9]}${d[10]}`
}

// ─── CNPJ Generator ──────────────────────────────────────────────────────────

function calcCnpjDigit(partial: number[], weights: number[]): number {
  let sum = 0
  for (let i = 0; i < partial.length; i++) {
    sum += partial[i]! * weights[i]!
  }
  const rem = sum % 11
  return rem < 2 ? 0 : 11 - rem
}

export function generateCnpj(): string {
  const digits: number[] = []
  for (let i = 0; i < 8; i++) digits.push(nextInt(0, 9))
  // Branch + verificadores
  digits.push(0, 0, 0, 1)
  const w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
  const w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
  digits.push(calcCnpjDigit(digits, w1))
  digits.push(calcCnpjDigit(digits, w2))
  const d = digits
  return `${d[0]}${d[1]}.${d[2]}${d[3]}${d[4]}.${d[5]}${d[6]}${d[7]}/${d[8]}${d[9]}${d[10]}${d[11]}-${d[12]}${d[13]}`
}

// ─── Other BR generators ─────────────────────────────────────────────────────

export function generateName(): string {
  return `${pickFrom(BR_FIRST_NAMES)} ${pickFrom(BR_LAST_NAMES)}`
}

export function generateDate(): string {
  const year = nextInt(2020, 2025)
  const month = nextInt(1, 12)
  const day = nextInt(1, 28)
  return `${String(day).padStart(2, '0')}/${String(month).padStart(2, '0')}/${year}`
}

export function generateIsoDate(): string {
  const year = nextInt(2020, 2025)
  const month = nextInt(1, 12)
  const day = nextInt(1, 28)
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

export function generateCurrency(): string {
  const value = nextInt(10, 99999) + nextInt(0, 99) / 100
  return `R$ ${value.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export function generatePhone(): string {
  const ddd = nextInt(11, 99)
  const num1 = nextInt(90000, 99999)
  const num2 = nextInt(1000, 9999)
  return `(${ddd})${num1}-${num2}`
}

export function generateAddress(): string {
  return `${pickFrom(BR_STREETS)}, ${nextInt(1, 9999)}`
}

export function generateCity(): string {
  return pickFrom(BR_CITIES)
}

export function generateState(): string {
  return pickFrom(BR_STATES)
}

export function generateCep(): string {
  const part1 = String(nextInt(10000, 99999)).padStart(5, '0')
  const part2 = String(nextInt(100, 999)).padStart(3, '0')
  return `${part1}-${part2}`
}

// ─── Type-based value generator ──────────────────────────────────────────────

/** Detect semantic hints from a field path/name */
function detectSemanticType(path: string): string | null {
  const lower = path.toLowerCase()
  if (lower.includes('cpf')) return 'cpf'
  if (lower.includes('cnpj')) return 'cnpj'
  if (lower.includes('telefone') || lower.includes('phone') || lower.includes('cel')) return 'phone'
  if (lower.includes('cep') || lower.includes('postal')) return 'cep'
  if (
    lower.includes('nome') ||
    lower.includes('name') ||
    lower.includes('razao') ||
    lower.includes('cliente')
  )
    return 'name'
  if (lower.includes('cidade') || lower.includes('city') || lower.includes('municipio'))
    return 'city'
  if (lower.includes('estado') || lower.includes('uf') || lower.includes('state')) return 'state'
  if (lower.includes('endereco') || lower.includes('logradouro') || lower.includes('address'))
    return 'address'
  if (
    lower.includes('valor') ||
    lower.includes('preco') ||
    lower.includes('total') ||
    lower.includes('saldo') ||
    lower.includes('currency')
  )
    return 'currency'
  if (
    lower.includes('data') ||
    lower.includes('date') ||
    lower.includes('nascimento') ||
    lower.includes('vencimento')
  )
    return 'date'
  return null
}

export function generateValueForField(fieldPath: string, xsdType: string): unknown {
  const semantic = detectSemanticType(fieldPath)

  // Semantic overrides
  switch (semantic) {
    case 'cpf':
      return generateCpf()
    case 'cnpj':
      return generateCnpj()
    case 'phone':
      return generatePhone()
    case 'cep':
      return generateCep()
    case 'name':
      return generateName()
    case 'city':
      return generateCity()
    case 'state':
      return generateState()
    case 'address':
      return generateAddress()
    case 'currency':
      return generateCurrency()
    case 'date':
      return generateDate()
  }

  // XSD type fallback
  switch (xsdType) {
    case 'integer':
      return nextInt(1, 9999)
    case 'decimal':
      return Math.round((nextInt(1, 9999) + nextInt(0, 99) / 100) * 100) / 100
    case 'boolean':
      return nextInt(0, 1) === 1
    case 'date':
      return generateIsoDate()
    case 'string':
    default: {
      // Generic names for unrecognized string fields
      const genericValues = [
        generateName(),
        'Descrição de exemplo',
        'Texto de teste',
        `Item ${nextInt(1, 999)}`,
        'Valor padrão',
      ]
      return pickFrom(genericValues)
    }
  }
}

// ─── Build nested object from XSD field paths ────────────────────────────────

function setNestedValue(
  obj: Record<string, unknown>,
  pathParts: string[],
  value: unknown,
  arraySize: number,
  isArray: boolean,
): void {
  if (pathParts.length === 0) return

  const [head, ...rest] = pathParts as [string, ...string[]]

  if (rest.length === 0) {
    if (isArray) {
      obj[head] = Array.from({ length: arraySize }, (_, i) =>
        typeof value === 'object' && value !== null
          ? { ...(value as Record<string, unknown>) }
          : `Item ${i + 1}`,
      )
    } else {
      obj[head] = value
    }
    return
  }

  if (!(head in obj) || typeof obj[head] !== 'object' || obj[head] === null) {
    obj[head] = {}
  }
  setNestedValue(obj[head] as Record<string, unknown>, rest, value, arraySize, isArray)
}

// ─── Main generator ──────────────────────────────────────────────────────────

/**
 * Generate synthetic JSON data from XSD field definitions.
 *
 * @param xsdFields - field definitions from mappingStore
 * @param size - 'small' | 'medium' | 'large' controls array lengths
 * @returns generated fields as a nested Record
 */
export function generateSyntheticData(
  xsdFields: XsdFieldDef[],
  size: SyntheticSize,
): Record<string, unknown> {
  const arraySize = ARRAY_SIZES[size]
  const result: Record<string, unknown> = {}

  for (const field of xsdFields) {
    const parts = field.path.split('.')
    const isArray = field.type === 'array'

    if (isArray) {
      // Generate array of objects with child fields
      const arrayItems = Array.from({ length: arraySize }, () => {
        const item: Record<string, unknown> = {}
        // Add child fields that belong to this array
        for (const other of xsdFields) {
          if (other.path.startsWith(field.path + '.')) {
            const childPath = other.path.slice(field.path.length + 1)
            const childParts = childPath.split('.')
            setNestedValue(
              item,
              childParts,
              generateValueForField(other.path, other.type),
              arraySize,
              other.type === 'array',
            )
          }
        }
        // If no child fields found, generate a default item
        if (Object.keys(item).length === 0) {
          item['valor'] = generateValueForField(field.path, 'string')
          item['descricao'] = `Item de ${field.path}`
        }
        return item
      })
      const topParts = parts
      let obj = result
      for (let i = 0; i < topParts.length - 1; i++) {
        const key = topParts[i]!
        if (!(key in obj) || typeof obj[key] !== 'object' || obj[key] === null) {
          obj[key] = {}
        }
        obj = obj[key] as Record<string, unknown>
      }
      const lastKey = topParts[topParts.length - 1]!
      obj[lastKey] = arrayItems
    } else {
      // Skip child fields of arrays (handled above)
      const isChildOfArray = xsdFields.some(
        (f) => f.type === 'array' && field.path.startsWith(f.path + '.'),
      )
      if (isChildOfArray) continue

      const value = generateValueForField(field.path, field.type)
      setNestedValue(result, parts, value, arraySize, false)
    }
  }

  // If no fields defined, generate a minimal sample
  if (Object.keys(result).length === 0) {
    result['nome'] = generateName()
    result['cpf'] = generateCpf()
    result['data'] = generateDate()
    result['valor'] = generateCurrency()
    result['items'] = Array.from({ length: arraySize }, (_, i) => ({
      descricao: `Item ${i + 1}`,
      quantidade: nextInt(1, 10),
      unitario: Math.round(nextInt(10, 9999) * 100) / 100,
    }))
  }

  return result
}

/** Dataset name by size */
export const SYNTHETIC_NAMES: Record<SyntheticSize, string> = {
  small: 'synthetic_small',
  medium: 'synthetic_medium',
  large: 'synthetic_large',
}
