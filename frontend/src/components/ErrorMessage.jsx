export default function ErrorMessage({ message = 'Something went wrong.', onRetry }) {
  return (
    <div className="max-w-md mx-auto mt-12 p-6 bg-red-50 border border-red-200 rounded-lg text-center">
      <p className="text-red-700 mb-3">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-sm text-red-600 underline hover:text-red-800"
        >
          Try again
        </button>
      )}
    </div>
  )
}
