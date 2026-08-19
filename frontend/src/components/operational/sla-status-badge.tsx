import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { ShieldCheck, ShieldAlert, Timer, Ban } from "lucide-react"

export type SLAStatus = "HEALTHY" | "AT_RISK" | "BREACHED" | "UNAVAILABLE"

interface SLAStatusBadgeProps {
  status: SLAStatus
  className?: string
}

export function SLAStatusBadge({ status, className }: SLAStatusBadgeProps) {
  const normalizedStatus = (status || "UNAVAILABLE").toUpperCase() as SLAStatus

  switch (normalizedStatus) {
    case "HEALTHY":
      return (
        <Badge variant="healthy" className={className}>
          <ShieldCheck className="w-3 h-3 mr-1" />
          HEALTHY
        </Badge>
      )
    case "AT_RISK":
      return (
        <Badge variant="warning" className={className}>
          <Timer className="w-3 h-3 mr-1" />
          AT RISK
        </Badge>
      )
    case "BREACHED":
      return (
        <Badge variant="critical" className={className}>
          <ShieldAlert className="w-3 h-3 mr-1" />
          BREACHED
        </Badge>
      )
    case "UNAVAILABLE":
    default:
      return (
        <Badge variant="unknown" className={className}>
          <Ban className="w-3 h-3 mr-1 opacity-50" />
          UNAVAILABLE
        </Badge>
      )
  }
}
