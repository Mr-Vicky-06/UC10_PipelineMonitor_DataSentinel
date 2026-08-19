import * as React from "react"
import { AlertCircle, AlertTriangle, CheckCircle2, Info, HelpCircle } from "lucide-react"
import { Badge } from "@/components/ui/badge"

export type SeverityLevel = "CRITICAL" | "ERROR" | "WARNING" | "INFO" | "UNKNOWN"

interface StatusBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  severity: SeverityLevel
  label?: string
}

export function StatusBadge({ severity, label, className, ...props }: StatusBadgeProps) {
  const config = {
    CRITICAL: { variant: "critical" as const, icon: AlertCircle, defaultLabel: "Critical" },
    ERROR: { variant: "critical" as const, icon: AlertTriangle, defaultLabel: "Error" },
    WARNING: { variant: "warning" as const, icon: AlertTriangle, defaultLabel: "Warning" },
    INFO: { variant: "running" as const, icon: Info, defaultLabel: "Info" },
    UNKNOWN: { variant: "unknown" as const, icon: HelpCircle, defaultLabel: "Unknown" },
  }

  const { variant, icon: Icon, defaultLabel } = config[severity] || config.UNKNOWN
  const displayLabel = label || defaultLabel

  return (
    <Badge variant={variant} className={`gap-1 pr-2.5 ${className}`} {...props}>
      <Icon className="h-3 w-3" />
      <span>{displayLabel}</span>
    </Badge>
  )
}
