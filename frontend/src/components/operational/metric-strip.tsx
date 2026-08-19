import * as React from "react"
import { cn } from "@/lib/utils"

interface MetricStripProps {
  children: React.ReactNode
  className?: string
}

export function MetricStrip({ children, className }: MetricStripProps) {
  return (
    <div className={cn("grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 divide-x divide-border-default border border-border-default bg-surface rounded-sm overflow-hidden", className)}>
      {children}
    </div>
  )
}

interface MetricItemProps {
  label: string
  value: string | number
  trend?: string
  trendDirection?: "up" | "down" | "neutral"
  status?: "healthy" | "warning" | "critical" | "neutral"
  icon?: React.ReactNode
  className?: string
}

export function MetricItem({ label, value, trend, trendDirection, status = "neutral", icon, className }: MetricItemProps) {
  
  const statusColors = {
    healthy: "text-status-success",
    warning: "text-status-warning",
    critical: "text-status-critical",
    neutral: "text-primary"
  }

  const trendColors = {
    up: "text-status-success",
    down: "text-status-critical",
    neutral: "text-secondary"
  }

  return (
    <div className={cn("flex flex-col p-3 transition-colors hover:bg-surface-hover", className)}>
      <div className="flex items-center text-xs text-secondary font-medium tracking-wide uppercase mb-1">
        {icon && <span className="mr-1.5 opacity-70">{icon}</span>}
        {label}
      </div>
      <div className="flex items-baseline space-x-2">
        <div className={cn("text-xl font-semibold tabular-nums", statusColors[status])}>
          {value}
        </div>
        {trend && (
          <div className={cn("text-xs font-medium", trendDirection ? trendColors[trendDirection] : "text-secondary")}>
            {trend}
          </div>
        )}
      </div>
    </div>
  )
}
