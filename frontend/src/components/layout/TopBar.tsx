import * as React from "react"
import { Search, Bell, Clock, RefreshCw } from "lucide-react"

export function TopBar() {
  return (
    <div className="flex h-16 shrink-0 items-center justify-between border-b border-border-default bg-surface px-8">
      <div className="flex flex-1 items-center gap-x-4 lg:gap-x-6">
        <form className="relative flex flex-1" action="#" method="GET">
          <label htmlFor="search-field" className="sr-only">
            Search pipelines, incidents, or hospitals...
          </label>
          <Search
            className="pointer-events-none absolute inset-y-0 left-0 h-full w-5 text-tertiary ml-2"
            aria-hidden="true"
          />
          <input
            id="search-field"
            className="block h-full w-full border-0 py-0 pl-10 pr-0 text-primary placeholder:text-tertiary focus:ring-0 sm:text-sm bg-transparent"
            placeholder="Search pipelines, incidents, or hospitals... (Press '/')"
            type="search"
            name="search"
          />
        </form>
      </div>
      
      <div className="flex items-center gap-x-4 lg:gap-x-6">
        {/* Time Range Selector */}
        <div className="hidden sm:flex items-center gap-2 border border-border-default rounded-md px-3 py-1.5 bg-canvas/50">
          <Clock className="h-4 w-4 text-secondary" />
          <select className="bg-transparent border-none text-sm font-medium text-secondary focus:ring-0 p-0 cursor-pointer">
            <option>Last 1 hour</option>
            <option>Last 6 hours</option>
            <option>Last 24 hours</option>
            <option>Last 7 days</option>
            <option>Last 30 days</option>
          </select>
        </div>

        {/* Auto Refresh Toggle */}
        <div className="hidden sm:flex items-center gap-2 border border-border-default rounded-md px-3 py-1.5 bg-canvas/50">
          <RefreshCw className="h-4 w-4 text-interactive" />
          <span className="text-sm font-medium text-secondary">Auto-refresh: ON</span>
        </div>

        {/* Separator */}
        <div className="hidden lg:block lg:h-6 lg:w-px lg:bg-border-default" aria-hidden="true" />

        {/* Notifications */}
        <button type="button" className="-m-2.5 p-2.5 text-secondary hover:text-primary relative">
          <span className="sr-only">View notifications</span>
          <Bell className="h-5 w-5" aria-hidden="true" />
          <span className="absolute top-2 right-2 flex h-2 w-2 rounded-full bg-status-critical"></span>
        </button>

        {/* Profile */}
        <div className="flex items-center gap-x-4 lg:gap-x-6">
          <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center border border-border-default text-sm font-medium text-primary">
            OP
          </div>
        </div>
      </div>
    </div>
  )
}
