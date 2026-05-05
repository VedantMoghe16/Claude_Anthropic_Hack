import { useContext } from "react"
import { AppContext } from "./appContextStore"

export function useAppContext() {
  const context = useContext(AppContext)

  if (!context) {
    throw new Error("useAppContext must be used within AppProvider")
  }

  return context
}
