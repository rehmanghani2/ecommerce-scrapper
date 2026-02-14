import React, { useEffect, useRef, useState } from 'react'
import {
  DocumentTextIcon,
  ArrowDownIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline'
import { cn, formatDate } from '@/utils/helpers'
import { Card, CardHeader, CardTitle, Button, Badge, EmptyState } from '@/components/Common'
import { useJobLogs } from '@/hooks/useJobs'

const LOG_LEVELS = {
  info: { color: 'bg-blue-500', label: 'INFO' },
  warning: { color: 'bg-warning-500', label: 'WARN' },
  error: { color: 'bg-danger-500', label: 'ERROR' },
  debug: { color: 'bg-gray-500', label: 'DEBUG' },
}

export function JobLogs({ jobId }) {
  const { data, isLoading } = useJobLogs(jobId)
  const containerRef = useRef(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const [filter, setFilter] = useState('all')

  const logs = data?.logs || []

  // Filter logs
  const filteredLogs = filter === 'all'
    ? logs
    : logs.filter((log) => log.level === filter)

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [logs, autoScroll])

  // Detect manual scroll
  const handleScroll = () => {
    if (!containerRef.current) return
    
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50
    setAutoScroll(isAtBottom)
  }

  return (
    <Card padding="none">
      <div className="flex items-center justify-between px-6 py-4 border-b dark:border-gray-700">
        <CardTitle className="flex items-center gap-2">
          <DocumentTextIcon className="w-5 h-5" />
          Logs
          <Badge variant="secondary" size="sm">
            {logs.length}
          </Badge>
        </CardTitle>
        
        <div className="flex items-center gap-2">
          {/* Filter dropdown */}
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5"
          >
            <option value="all">All levels</option>
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="error">Error</option>
            <option value="debug">Debug</option>
          </select>
          
          {/* Scroll to bottom button */}
          {!autoScroll && (
            <Button
              size="sm"
              variant="ghost"
              icon={ArrowDownIcon}
              onClick={() => {
                setAutoScroll(true)
                if (containerRef.current) {
                  containerRef.current.scrollTop = containerRef.current.scrollHeight
                }
              }}
            >
              Scroll to bottom
            </Button>
          )}
        </div>
      </div>

      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="h-96 overflow-y-auto font-mono text-sm"
      >
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500">Loading logs...</p>
          </div>
        ) : filteredLogs.length === 0 ? (
          <EmptyState
            icon={DocumentTextIcon}
            title="No logs"
            description={filter !== 'all' ? 'No logs match the selected filter.' : 'No logs available yet.'}
          />
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {filteredLogs.map((log, index) => (
              <LogEntry key={index} log={log} />
            ))}
          </div>
        )}
      </div>
    </Card>
  )
}

function LogEntry({ log }) {
  const levelConfig = LOG_LEVELS[log.level] || LOG_LEVELS.info
  
  return (
    <div className="px-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-800/50 flex items-start gap-3">
      <span className="text-xs text-gray-400 dark:text-gray-500 shrink-0 w-20">
        {formatDate(log.timestamp, 'HH:mm:ss')}
      </span>
      
      <span
        className={cn(
          'px-1.5 py-0.5 text-xs font-medium text-white rounded shrink-0',
          levelConfig.color
        )}
      >
        {levelConfig.label}
      </span>
      
      <span
        className={cn(
          'flex-1 break-all',
          log.level === 'error' && 'text-danger-600 dark:text-danger-400',
          log.level === 'warning' && 'text-warning-600 dark:text-warning-400',
          log.level === 'debug' && 'text-gray-500 dark:text-gray-400'
        )}
      >
        {log.message}
      </span>
    </div>
  )
}

export default JobLogs