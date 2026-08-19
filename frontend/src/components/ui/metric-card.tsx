import * as React from "react"
import { Card, CardContent } from "@/components/ui/card"
import { ArrowDownIcon, ArrowUpIcon, MinusIcon } from "lucide-react"
import { cn } from "@/lib/utils"

interface MetricCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string
  value: string | number
  delta?: string | number
  trend?: "up" | "down" | "neutral"
  trendLabel?: string
  trendValue?: string
  icon?: React.ReactNode
}

export function MetricCard({
  title,
  value,
  delta,
  trend,
  trendLabel,
  trendValue,
  icon,
  className,
  ...props
}: MetricCardProps) {
  const displayLabel = trendLabel || trendValue
  
  return (
    <Card className={cn("overflow-hidden", className)} {...props}>
      <CardContent className="p-4 sm:p-6 flex flex-col justify-between h-full">
        <div className="flex justify-between items-start">
          <p className="text-sm font-medium text-secondary truncate">{title}</p>
          {icon && <div className="text-tertiary h-4 w-4">{icon}</div>}
        </div>
        
        <div className="mt-4 flex items-baseline gap-2">
          <span className="text-2xl sm:text-3xl font-semibold tracking-tight text-primary tabular-nums">
            {value}
          </span>
          
          {(delta !== undefined || trend) && (
            <div className="flex items-center text-xs font-medium">
              {trend === "up" && <ArrowUpIcon className="mr-1 h-3 w-3 text-status-success" />}
              {trend === "down" && <ArrowDownIcon className="mr-1 h-3 w-3 text-status-error" />}
              {trend === "neutral" && <MinusIcon className="mr-1 h-3 w-3 text-secondary" />}
              
              <span className={cn(
                trend === "up" ? "text-status-success" : 
                trend === "down" ? "text-status-error" : "text-secondary",
                "tabular-nums"
              )}>
                {delta}
              </span>
              
              {displayLabel && (
                <span className="ml-1 text-tertiary">{displayLabel}</span>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
