import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowDownTrayIcon,
  DocumentTextIcon,
  TableCellsIcon,
  CodeBracketIcon,
  TrashIcon,
  FolderOpenIcon,
} from '@heroicons/react/24/outline'
import { cn, formatFileSize, formatDate } from '@/utils/helpers'
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  EmptyState,
  PageLoader,
  ConfirmModal,
} from '@/components/Common'
import exportService from '@/services/exportService'
import toast from 'react-hot-toast'

const FORMAT_ICONS = {
  csv: DocumentTextIcon,
  xlsx: TableCellsIcon,
  json: CodeBracketIcon,
}

const FORMAT_COLORS = {
  csv: 'text-green-600 bg-green-100 dark:bg-green-900/30 dark:text-green-400',
  xlsx: 'text-blue-600 bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400',
  json: 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30 dark:text-yellow-400',
}

export default function Exports() {
  const queryClient = useQueryClient()
  const [deleteModal, setDeleteModal] = useState({ open: false, filename: null })

  // Fetch exports
  const { data: exports, isLoading } = useQuery({
    queryKey: ['exports'],
    queryFn: () => exportService.listExports(),
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (filename) => exportService.deleteExport(filename),
    onSuccess: () => {
      toast.success('Export deleted')
      queryClient.invalidateQueries(['exports'])
      setDeleteModal({ open: false, filename: null })
    },
    onError: () => {
      toast.error('Failed to delete export')
    },
  })

  // Download handler
  const handleDownload = async (filename) => {
    try {
      await exportService.downloadExport(filename)
      toast.success('Download started')
    } catch (error) {
      toast.error('Failed to download file')
    }
  }

  const getFileFormat = (filename) => {
    const ext = filename.split('.').pop().toLowerCase()
    return ext === 'xlsx' ? 'xlsx' : ext
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <ArrowDownTrayIcon className="w-8 h-8 text-primary-600" />
            Exports
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Download your exported data files
          </p>
        </div>
      </div>

      {/* Exports List */}
      {isLoading ? (
        <PageLoader message="Loading exports..." />
      ) : !exports || exports.length === 0 ? (
        <EmptyState
          icon={FolderOpenIcon}
          title="No exports yet"
          description="When you export data from a job, the files will appear here for download."
        />
      ) : (
        <Card padding="none">
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {exports.map((file) => {
              const format = getFileFormat(file.filename)
              const Icon = FORMAT_ICONS[format] || DocumentTextIcon
              
              return (
                <div
                  key={file.filename}
                  className="flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50"
                >
                  <div className="flex items-center gap-4">
                    <div className={cn('p-3 rounded-lg', FORMAT_COLORS[format])}>
                      <Icon className="w-6 h-6" />
                    </div>
                    
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">
                        {file.filename}
                      </p>
                      <div className="flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
                        <span>{formatFileSize(file.size)}</span>
                        <span>•</span>
                        <span>{formatDate(file.created_at)}</span>
                        <span>•</span>
                        <span className="uppercase">{format}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      icon={ArrowDownTrayIcon}
                      onClick={() => handleDownload(file.filename)}
                    >
                      Download
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      icon={TrashIcon}
                      onClick={() => setDeleteModal({ open: true, filename: file.filename })}
                      className="text-danger-600 hover:text-danger-700 hover:bg-danger-50 dark:text-danger-400 dark:hover:bg-danger-900/20"
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </Card>
      )}

      {/* Storage Info */}
      {exports && exports.length > 0 && (
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Total Storage Used</p>
              <p className="text-xl font-bold text-gray-900 dark:text-white">
                {formatFileSize(exports.reduce((sum, f) => sum + f.size, 0))}
              </p>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {exports.length} file{exports.length !== 1 ? 's' : ''}
            </p>
          </div>
        </Card>
      )}

      {/* Delete Confirmation */}
      <ConfirmModal
        isOpen={deleteModal.open}
        onClose={() => setDeleteModal({ open: false, filename: null })}
        onConfirm={() => deleteMutation.mutate(deleteModal.filename)}
        title="Delete Export"
        message={`Are you sure you want to delete "${deleteModal.filename}"? This action cannot be undone.`}
        confirmText="Delete"
        loading={deleteMutation.isPending}
      />
    </div>
  )
}