import * as React from "react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"

interface Column<T> {
  header: React.ReactNode
  accessorKey?: keyof T
  cell?: (row: T) => React.ReactNode
  className?: string
}

interface OperationalTableProps<T> {
  data: T[]
  columns: Column<T>[]
  onRowClick?: (row: T) => void
  emptyMessage?: React.ReactNode
  className?: string
}

export function OperationalTable<T>({ 
  data, 
  columns, 
  onRowClick, 
  emptyMessage = "No data available",
  className 
}: OperationalTableProps<T>) {
  
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center p-8 text-secondary text-sm border border-border-default rounded-sm bg-surface">
        {emptyMessage}
      </div>
    )
  }

  return (
    <div className={cn("rounded-sm border border-border-default bg-surface overflow-hidden", className)}>
      <Table>
        <TableHeader className="bg-canvas">
          <TableRow className="hover:bg-transparent">
            {columns.map((col, i) => (
              <TableHead 
                key={i} 
                className={cn("h-9 py-2 text-xs font-semibold text-secondary uppercase tracking-wider", col.className)}
              >
                {col.header}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((row, rowIndex) => (
            <TableRow 
              key={rowIndex}
              onClick={() => onRowClick && onRowClick(row)}
              className={cn(
                "group transition-colors",
                onRowClick && "cursor-pointer hover:bg-surface-hover"
              )}
            >
              {columns.map((col, colIndex) => (
                <TableCell 
                  key={colIndex} 
                  className={cn("py-2 px-4 text-sm", col.className)}
                >
                  {col.cell ? col.cell(row) : col.accessorKey ? String(row[col.accessorKey]) : null}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
