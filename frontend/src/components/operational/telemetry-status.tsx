"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { formatDistanceToNowStrict } from "date-fns"

export type TelemetryState = "LIVE" | "STALE" | "OFFLINE"

interface TelemetryStatusProps {
  lastUpdated: Date | null
  isError: boolean
  staleThresholdMs?: number
  className?: string
}

export function TelemetryStatus({
  lastUpdated,
  isError,
  staleThresholdMs = 15000,
  className
}: TelemetryStatusProps) {
  const [now, setNow] = React.useState(new Date())

  // Force re-render every second to update the relative time
  React.useEffect(() => {
    const interval = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(interval)
  }, [])

  let state: TelemetryState = "LIVE"
  let message = "Awaiting data..."

  if (isError) {
    state = "OFFLINE"
    message = "Disconnected"
  } else if (!lastUpdated) {
    state = "STALE"
    message = "Sync delayed"
  } else {
    const msSinceUpdate = now.getTime() - lastUpdated.getTime()
    if (msSinceUpdate > staleThresholdMs) {
      state = "STALE"
      message = `Sync delayed (${formatDistanceToNowStrict(lastUpdated)} ago)`
    } else {
      state = "LIVE"
      message = `Updated ${formatDistanceToNowStrict(lastUpdated)} ago`
    }
  }

  const dotClasses = {
    LIVE: "bg-status-success shadow-[0_0_8px_rgba(16,185,129,0.5)]",
    STALE: "bg-status-warning",
    OFFLINE: "bg-status-critical"
  }

  return (
    <div className={cn("flex items-center space-x-2 text-xs font-mono", className)}>
      <div className="relative flex h-2.5 w-2.5 items-center justify-center">
        {state === "LIVE" && (
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-status-success opacity-20"></span>
        )}
        <span className={cn("relative inline-flex h-2 w-2 rounded-full", dotClasses[state])}></span>
      </div>
      <div className={cn(
        "font-medium",
        state === "LIVE" ? "text-primary" : "text-secondary"
      )}>
        {state}
        <span className="mx-1.5 opacity-50">·</span>
        <span className="text-secondary font-normal">{message}</span>
      </div>
    </div>
  )
}
