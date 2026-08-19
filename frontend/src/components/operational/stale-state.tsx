import * as React from "react"
import { Clock } from "lucide-react"
import { cn } from "@/lib/utils"

interface StaleStateProps {
  title?: string
  message?: string
  className?: string
}

export function StaleState({ 
  title = "Data Stale", 
  message = "Waiting for updated telemetry...", 
  className 
}: StaleStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center py-12 px-4 text-center rounded-md border border-dashed border-status-warning/50 bg-surface", className)}>
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-status-warning/10 mb-4">
        <Clock className="h-6 w-6 text-status-warning" />
      </div>
      <h3 className="text-sm font-semibold text-primary">{title}</h3>
      <p className="text-sm text-secondary mt-1 max-w-sm">{message}</p>
    </div>
  )
}
