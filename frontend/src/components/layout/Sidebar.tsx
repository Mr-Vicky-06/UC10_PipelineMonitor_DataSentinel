'use client';
import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { 
  Activity, 
  GitCommit, 
  ShieldCheck, 
  LineChart, 
  AlertTriangle,
  BarChart3,
  Settings
} from "lucide-react"

import { cn } from "@/lib/utils"

const navigation = [
  { name: "Operations Center", href: "/", icon: Activity },
  { name: "Pipeline Runs", href: "/pipelines", icon: GitCommit },
  { name: "Data Quality", href: "/data-quality", icon: ShieldCheck },
  { name: "Anomalies", href: "/anomalies", icon: LineChart },
  { name: "Incidents", href: "/incidents", icon: AlertTriangle },
]

const secondaryNavigation = [
  { name: "Analytics", href: "/analytics", icon: BarChart3 },
  { name: "Settings", href: "/settings", icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <div className="flex h-full w-64 flex-col border-r border-border-default bg-surface">
      <div className="flex h-16 shrink-0 items-center px-6">
        <ShieldCheck className="h-6 w-6 text-interactive" />
        <span className="ml-3 text-lg font-semibold tracking-tight text-primary">
          DATASENTINEL
        </span>
      </div>
      
      <div className="flex flex-1 flex-col overflow-y-auto px-4 py-4">
        <nav className="flex-1 space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href || (item.href !== "/" && pathname?.startsWith(item.href))
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  isActive
                    ? "bg-muted text-primary"
                    : "text-secondary hover:bg-surface-hover hover:text-primary",
                  "group flex items-center rounded-md px-2 py-2 text-sm font-medium"
                )}
              >
                <item.icon
                  className={cn(
                    isActive ? "text-interactive" : "text-tertiary group-hover:text-secondary",
                    "mr-3 h-5 w-5 flex-shrink-0"
                  )}
                  aria-hidden="true"
                />
                {item.name}
              </Link>
            )
          })}
        </nav>
        
        <div className="mt-8">
          <div className="h-px bg-border-default w-full my-4" />
          <nav className="space-y-1">
            {secondaryNavigation.map((item) => {
              const isActive = pathname === item.href
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    isActive
                      ? "bg-muted text-primary"
                      : "text-secondary hover:bg-surface-hover hover:text-primary",
                    "group flex items-center rounded-md px-2 py-2 text-sm font-medium"
                  )}
                >
                  <item.icon
                    className={cn(
                      isActive ? "text-interactive" : "text-tertiary group-hover:text-secondary",
                      "mr-3 h-5 w-5 flex-shrink-0"
                    )}
                    aria-hidden="true"
                  />
                  {item.name}
                </Link>
              )
            })}
          </nav>
        </div>
      </div>
      
      {/* Global Status Footer */}
      <div className="border-t border-border-default p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <div className="h-2.5 w-2.5 rounded-full bg-status-success animate-pulse"></div>
            <span className="ml-2 text-sm font-medium text-secondary">System Healthy</span>
          </div>
          <div className="flex items-center justify-center rounded-sm bg-status-critical px-2 py-0.5 text-xs font-medium text-inverse">
            0
          </div>
        </div>
      </div>
    </div>
  )
}
