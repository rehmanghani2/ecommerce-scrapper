import React from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Line, Bar } from 'react-chartjs-2'
import { Card, CardHeader, CardTitle } from '@/components/Common'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

// Sample data - in real app, this would come from API
const generateSampleData = () => {
  const labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  
  return {
    labels,
    datasets: [
      {
        label: 'Products Scraped',
        data: [1200, 1900, 3000, 2500, 2780, 1890, 2390],
        borderColor: 'rgb(37, 99, 235)',
        backgroundColor: 'rgba(37, 99, 235, 0.1)',
        fill: true,
        tension: 0.4,
      },
    ],
  }
}

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false,
    },
    tooltip: {
      backgroundColor: '#1f2937',
      titleColor: '#f9fafb',
      bodyColor: '#f9fafb',
      padding: 12,
      cornerRadius: 8,
    },
  },
  scales: {
    x: {
      grid: {
        display: false,
      },
      ticks: {
        color: '#9ca3af',
      },
    },
    y: {
      grid: {
        color: 'rgba(156, 163, 175, 0.1)',
      },
      ticks: {
        color: '#9ca3af',
      },
    },
  },
}

export function ActivityChart() {
  const data = generateSampleData()

  return (
    <Card>
      <CardHeader>
        <CardTitle>Scraping Activity</CardTitle>
      </CardHeader>
      
      <div className="h-64">
        <Line data={data} options={chartOptions} />
      </div>
    </Card>
  )
}

// Jobs by status chart
export function JobsStatusChart() {
  const data = {
    labels: ['Completed', 'Running', 'Failed', 'Pending'],
    datasets: [
      {
        data: [45, 8, 5, 12],
        backgroundColor: [
          'rgba(34, 197, 94, 0.8)',
          'rgba(37, 99, 235, 0.8)',
          'rgba(239, 68, 68, 0.8)',
          'rgba(156, 163, 175, 0.8)',
        ],
        borderRadius: 4,
      },
    ],
  }

  const options = {
    ...chartOptions,
    indexAxis: 'y',
    plugins: {
      ...chartOptions.plugins,
      legend: {
        display: false,
      },
    },
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Jobs by Status</CardTitle>
      </CardHeader>
      
      <div className="h-48">
        <Bar data={data} options={options} />
      </div>
    </Card>
  )
}

export default ActivityChart