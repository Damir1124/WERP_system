import { createContext, useContext } from 'react'

// Контекст для обновления данных текущей страницы (пул) через refresh-FAB.
// Вынесен в отдельный файл, чтобы избежать циклического импорта между App.jsx и Pool.jsx.
const RefreshContext = createContext(null)

export function useRefresh() {
  return useContext(RefreshContext)
}

export default RefreshContext
