import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { AlertTriangle, AlertCircle, Info, ShieldAlert, HelpCircle } from "lucide-react"

export type SeverityLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN"

interface SeverityBadgeProps {
  severity: SeverityLevel
  className?: string
}

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  const normalizedSeverity = (severity || "UNKNOWN").toUpperCase() as SeverityLevel

  switch (normalizedSeverity) {
    case "CRITICAL":
      return (
        <Badge variant="critical" className={className}>
          <ShieldAlert className="w-3 h-3 mr-1" />
          CRITICAL
        </Badge>
      )
    case "HIGH":
      return (
        <Badge variant="warning" className={className}>
          <AlertTriangle className="w-3 h-3 mr-1" />
          HIGH
        </Badge>
      )
    case "MEDIUM":
      return (
        <Badge variant="warning" className={className}>
          <AlertCircle className="w-3 h-3 mr-1" />
          MEDIUM
        </Badge>
      )
    case "LOW":
      return (
        <Badge variant="outline" className={className}>
          <Info className="w-3 h-3 mr-1" />
          LOW
        </Badge>
      )
    default:
      return (
        <Badge variant="unknown" className={className}>
          <HelpCircle className="w-3 h-3 mr-1 opacity-50" />
          UNKNOWN
        </Badge>
      )
  }
}
