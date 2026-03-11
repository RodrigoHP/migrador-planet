import { defineStore } from 'pinia'

export interface LayoutStore {
  pageSize: 'A4' | 'Letter' | 'A3'
  marginTop: number
  marginBottom: number
  marginLeft: number
  marginRight: number
  baseFontFamily: string
  baseFontSize: number
  primaryColor: string
  lineHeight: number
  bibliotecasVersions: Record<string, string>
  confirmed: boolean
}

export const useLayoutStore = defineStore('layout', {
  state: (): LayoutStore => ({
    pageSize: 'A4',
    marginTop: 20,
    marginBottom: 20,
    marginLeft: 20,
    marginRight: 20,
    baseFontFamily: 'Inter',
    baseFontSize: 14,
    primaryColor: '#2563EB',
    lineHeight: 1.5,
    bibliotecasVersions: {},
    confirmed: false,
  }),
})
