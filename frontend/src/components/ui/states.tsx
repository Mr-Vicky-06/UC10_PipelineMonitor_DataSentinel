import * as React from "react"
import { AlertCircle, FileX2, Loader2, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"

interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string
  description?: string
  icon?: React.ElementType
  action?: {
    label: string
    onClick: () => void
  }
}

export function EmptyState({ title, description, icon: Icon = FileX2, action, className, ...props }: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center p-8 text-center border border-dashed border-border-default rounded-md bg-canvas/50 ${className}`} {...props}>
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted mb-4">
        <Icon className="h-6 w-6 text-tertiary" />
      </div>
      <h3 className="text-lg font-medium text-primary">{title}</h3>
      {description && <p className="mt-1 text-sm text-secondary max-w-sm">{description}</p>}
      {action && (
        <Button onClick={action.onClick} variant="outline" className="mt-4">
          {action.label}
        </Button>
      )}
    </div>
  )
}

interface LoadingStateProps extends React.HTMLAttributes<HTMLDivElement> {
  message?: string
}

export function LoadingState({ message = "Loading data...", className, ...props }: LoadingStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center p-12 text-center ${className}`} {...props}>
      <Loader2 className="h-8 w-8 text-interactive animate-spin mb-4" />
      <p className="text-sm font-medium text-secondary">{message}</p>
    </div>
  )
}

interface ErrorStateProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string
  message: string
  onRetry?: () => void
}

export function ErrorState({ title = "Error Loading Data", message, onRetry, className, ...props }: ErrorStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center p-8 text-center border border-status-error/20 bg-status-error/5 rounded-md ${className}`} {...props}>
      <AlertCircle className="h-8 w-8 text-status-error mb-4" />
      <h3 className="text-lg font-medium text-primary">{title}</h3>
      <p className="mt-1 text-sm text-status-error max-w-md">{message}</p>
      {onRetry && (
        <Button onClick={onRetry} variant="outline" className="mt-4 gap-2">
          <RefreshCw className="h-4 w-4" />
          Retry
        </Button>
      )}
    </div>
  )
}
