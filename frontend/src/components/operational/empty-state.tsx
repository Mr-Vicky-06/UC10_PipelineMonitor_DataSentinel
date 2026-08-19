import * as React from "react"
import { CheckCircle2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface EmptyStateProps {
  title: string
  message: string
  icon?: React.ReactNode
  className?: string
}

export function EmptyState({ title, message, icon, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center py-12 px-4 text-center rounded-md border border-dashed border-border-default bg-surface", className)}>
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-status-success/10 mb-4">
        {icon || <CheckCircle2 className="h-6 w-6 text-status-success" />}
      </div>
      <h3 className="text-sm font-semibold text-primary">{title}</h3>
      <p className="text-sm text-secondary mt-1 max-w-sm">{message}</p>
    </div>
  )
}
