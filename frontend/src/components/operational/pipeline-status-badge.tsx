import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { PlayCircle, CheckCircle2, XCircle, Clock } from "lucide-react"

export type PipelineStatus = "STARTED" | "COMPLETED" | "FAILED" | "PENDING" | "UNKNOWN"

interface PipelineStatusBadgeProps {
  status: PipelineStatus
  className?: string
}

export function PipelineStatusBadge({ status, className }: PipelineStatusBadgeProps) {
  const normalizedStatus = (status || "UNKNOWN").toUpperCase() as PipelineStatus

  switch (normalizedStatus) {
    case "STARTED":
      return (
        <Badge variant="running" className={className}>
          <PlayCircle className="w-3 h-3 mr-1 animate-pulse" />
          STARTED
        </Badge>
      )
    case "COMPLETED":
      return (
        <Badge variant="healthy" className={className}>
          <CheckCircle2 className="w-3 h-3 mr-1" />
          COMPLETED
        </Badge>
      )
    case "FAILED":
      return (
        <Badge variant="critical" className={className}>
          <XCircle className="w-3 h-3 mr-1" />
          FAILED
        </Badge>
      )
    case "PENDING":
      return (
        <Badge variant="outline" className={className}>
          <Clock className="w-3 h-3 mr-1" />
          PENDING
        </Badge>
      )
    default:
      return (
        <Badge variant="unknown" className={className}>
          UNKNOWN
        </Badge>
      )
  }
}
