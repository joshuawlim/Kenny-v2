// 404 Not Found page
import React from 'react'
import { Home, ArrowLeft } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'

export const NotFoundPage: React.FC = () => {
  const navigate = useNavigate()

  return (
    <div className="text-center py-16">
      <div className="glass-card rounded-2xl p-12 max-w-md mx-auto">
        <div className="text-6xl font-bold text-kenny-primary mb-4">404</div>
        <h1 className="text-2xl font-bold text-kenny-gray-800 mb-2">
          Page Not Found
        </h1>
        <p className="text-kenny-gray-600 mb-8">
          The page you're looking for doesn't exist or has been moved.
        </p>
        
        <div className="space-y-3">
          <button
            onClick={() => navigate(-1)}
            className="button-secondary w-full flex items-center justify-center space-x-2"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Go Back</span>
          </button>
          
          <Link
            to="/"
            className="button-primary w-full flex items-center justify-center space-x-2"
          >
            <Home className="w-4 h-4" />
            <span>Go to Dashboard</span>
          </Link>
        </div>
      </div>
    </div>
  )
}