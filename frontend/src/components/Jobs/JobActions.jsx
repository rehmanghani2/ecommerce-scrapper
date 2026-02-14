import React, { useState } from 'react'
import {
  EllipsisVerticalIcon,
  PlayIcon,
  PauseIcon,
  StopIcon,
  ArrowPathIcon,
  TrashIcon,
  ArrowDownTrayIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/helpers'
import {
  Dropdown,
  DropdownItem,
  DropdownDivider,
  IconButton,
  ConfirmModal,
} from '@/components/Common'
import { useJobActions } from '@/hooks/useJobs'

export function JobActions({ job, onAction, compact = false }) {
  const [confirmModal, setConfirmModal] = useState({ open: false, action: null })
  const { pauseJob, resumeJob, cancelJob, retryJob, deleteJob } = useJobActions()

  const handleAction = async (action) => {
    switch (action) {
      case 'pause':
        pauseJob.mutate(job.job_id)
        break
      case 'resume':
        resumeJob.mutate(job.job_id)
        break
      case 'cancel':
        cancelJob.mutate(job.job_id)
        break
      case 'retry':
        retryJob.mutate(job.job_id)
        break
      case 'delete':
        deleteJob.mutate(job.job_id)
        break
      case 'export':
        onAction?.('export', job)
        break
    }
    setConfirmModal({ open: false, action: null })
  }

  const confirmAndAction = (action, message) => {
    setConfirmModal({ open: true, action, message })
  }

  const getAvailableActions = () => {
    const actions = []
    
    switch (job.status) {
      case 'running':
        actions.push({ key: 'pause', label: 'Pause', icon: PauseIcon })
        actions.push({ key: 'cancel', label: 'Cancel', icon: StopIcon, danger: true, confirm: true })
        break
      case 'paused':
        actions.push({ key: 'resume', label: 'Resume', icon: PlayIcon })
        actions.push({ key: 'cancel', label: 'Cancel', icon: StopIcon, danger: true, confirm: true })
        break
      case 'failed':
        actions.push({ key: 'retry', label: 'Retry', icon: ArrowPathIcon })
        actions.push({ key: 'delete', label: 'Delete', icon: TrashIcon, danger: true, confirm: true })
        break
      case 'completed':
        actions.push({ key: 'export', label: 'Export', icon: ArrowDownTrayIcon })
        actions.push({ key: 'delete', label: 'Delete', icon: TrashIcon, danger: true, confirm: true })
        break
      case 'cancelled':
      case 'pending':
        actions.push({ key: 'delete', label: 'Delete', icon: TrashIcon, danger: true, confirm: true })
        break
    }
    
    return actions
  }

  const actions = getAvailableActions()

  if (actions.length === 0) return null

  return (
    <>
      <Dropdown
        trigger={
          <IconButton
            icon={EllipsisVerticalIcon}
            variant="ghost"
            size={compact ? 'sm' : 'md'}
          />
        }
        align="right"
      >
        {actions.map((action, index) => (
          <React.Fragment key={action.key}>
            {index > 0 && action.danger && <DropdownDivider />}
            <DropdownItem
              icon={action.icon}
              onClick={() => {
                if (action.confirm) {
                  confirmAndAction(action.key, `Are you sure you want to ${action.label.toLowerCase()} this job?`)
                } else {
                  handleAction(action.key)
                }
              }}
              danger={action.danger}
            >
              {action.label}
            </DropdownItem>
          </React.Fragment>
        ))}
      </Dropdown>

      <ConfirmModal
        isOpen={confirmModal.open}
        onClose={() => setConfirmModal({ open: false, action: null })}
        onConfirm={() => handleAction(confirmModal.action)}
        title="Confirm Action"
        message={confirmModal.message}
        confirmText="Confirm"
        variant="danger"
      />
    </>
  )
}

export default JobActions