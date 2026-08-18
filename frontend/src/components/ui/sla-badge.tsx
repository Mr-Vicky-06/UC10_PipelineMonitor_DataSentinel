import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { Clock } from "lucide-react"

export type SLAStatus = "ON_TRACK" | "AT_RISK" | "BREACHED" | "UNKNOWN"

interface SLABadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  status: SLAStatus
  eta?: string
  deadline?: string
}

export function SLABadge({ status, eta, deadline, className, ...props }: SLABadgeProps) {
  const config = {
    ON_TRACK: { variant: "success" as const, label: "On Track" },
    AT_RISK: { variant: "warning" as const, label: "At Risk" },
    BREACHED: { variant: "critical" as const, label: "Breached" },
    UNKNOWN: { variant: "secondary" as const, label: "Unknown" },
  }

  const { variant, label } = config[status] || config.UNKNOWN

  return (
    <div className={`inline-flex items-center gap-2 ${className}`} {...props}>
      <Badge variant={variant}>{label}</Badge>
      {eta && (
        <span className="inline-flex items-center text-xs text-secondary tabular-nums">
          <Clock className="mr-1 h-3 w-3" />
          ETA: {eta}
        </span>
      )}
    </div>
  )
}
