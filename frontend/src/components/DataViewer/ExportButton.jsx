import React, { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  ArrowDownTrayIcon,
  DocumentTextIcon,
  TableCellsIcon,
  CodeBracketIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/utils/helpers'
import {
  Button,
  Dropdown,
  DropdownItem,
  DropdownLabel,
  Modal,
  ModalFooter,
  Select,
  Progress,
} from '@/components/Common'
import exportService from '@/services/exportService'
import toast from 'react-hot-toast'

const EXPORT_FORMATS = [
  { value: 'csv', label: 'CSV', icon: DocumentTextIcon, description: 'Comma-separated values' },
  { value: 'excel', label: 'Excel', icon: TableCellsIcon, description: 'Microsoft Excel format' },
  { value: 'json', label: 'JSON', icon: CodeBracketIcon, description: 'JavaScript Object Notation' },
]

export function ExportButton({ jobId, disabled = false }) {
  const [modalOpen, setModalOpen] = useState(false)
  const [selectedFormat, setSelectedFormat] = useState('csv')

  const exportMutation = useMutation({
    mutationFn: () => exportService.createExport(jobId, selectedFormat),
    onSuccess: async (data) => {
      toast.success('Export created successfully!')
      setModalOpen(false)
      
      // Auto-download
      if (data.file_path) {
        const filename = data.file_path.split(/[/\\]/).pop()
        await exportService.downloadExport(filename)
      }
    },
    onError: (error) => {
      toast.error(error.message || 'Failed to create export')
    },
  })

  const handleQuickExport = (format) => {
    setSelectedFormat(format)
    exportMutation.mutate()
  }

  return (
    <>
      <Dropdown
        trigger={
          <Button
            icon={ArrowDownTrayIcon}
            variant="secondary"
            disabled={disabled}
          >
            Export
          </Button>
        }
        align="right"
      >
        <DropdownLabel>Export Format</DropdownLabel>
        {EXPORT_FORMATS.map((format) => (
          <DropdownItem
            key={format.value}
            icon={format.icon}
            onClick={() => handleQuickExport(format.value)}
          >
            <div>
              <p className="font-medium">{format.label}</p>
              <p className="text-xs text-gray-500">{format.description}</p>
            </div>
          </DropdownItem>
        ))}
      </Dropdown>

      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Export Products"
        size="sm"
      >
        <div className="space-y-4">
          <Select
            label="Export Format"
            options={EXPORT_FORMATS.map((f) => ({ value: f.value, label: f.label }))}
            value={selectedFormat}
            onChange={setSelectedFormat}
          />
          
          {exportMutation.isPending && (
            <div className="space-y-2">
              <p className="text-sm text-gray-500">Preparing export...</p>
              <Progress value={50} animated />
            </div>
          )}
        </div>

        <ModalFooter>
          <Button variant="secondary" onClick={() => setModalOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => exportMutation.mutate()}
            loading={exportMutation.isPending}
            icon={ArrowDownTrayIcon}
          >
            Export
          </Button>
        </ModalFooter>
      </Modal>
    </>
  )
}

export default ExportButton