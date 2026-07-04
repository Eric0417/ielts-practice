export default function LoadingSpinner({ message = 'Loading...' }) {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <div className="animate-spin rounded-full h-10 w-10 border-2 border-gray-300 border-t-green-600 mb-4" />
      <p className="text-gray-500 text-sm">{message}</p>
    </div>
  )
}
