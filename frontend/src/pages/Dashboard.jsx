import { Link } from 'react-router-dom'
import { BookOpen, Headphones, PenLine, BarChart3 } from 'lucide-react'

const cards = [
  {
    type: 'reading',
    icon: BookOpen,
    title: 'Reading',
    description: 'Practice reading comprehension with multiple-choice questions based on passages.',
    color: 'bg-blue-50 text-blue-600',
    hover: 'hover:border-blue-300',
  },
  {
    type: 'listening',
    icon: Headphones,
    title: 'Listening',
    description: 'Coming soon — listening practice with audio-based questions.',
    color: 'bg-purple-50 text-purple-600',
    hover: 'hover:border-purple-300',
    comingSoon: true,
  },
  {
    type: 'writing-task1',
    icon: BarChart3,
    title: 'Writing Task 1',
    description: 'Describe graphs, charts, and diagrams. 150-word minimum. AI-powered band score feedback.',
    color: 'bg-emerald-50 text-emerald-600',
    hover: 'hover:border-emerald-300',
  },
  {
    type: 'writing-task2',
    icon: PenLine,
    title: 'Writing Task 2',
    description: 'Write opinion and discussion essays. 250-word minimum. Detailed four-criteria AI grading.',
    color: 'bg-green-50 text-green-600',
    hover: 'hover:border-green-300',
  },
]

export default function Dashboard() {
  return (
    <div>
      {/* Hero */}
      <div className="text-center mb-12">
        <h1 className="text-3xl font-bold text-gray-900 mb-3">IELTS Practice Platform</h1>
        <p className="text-gray-500 max-w-md mx-auto">
          Choose a skill to practice. Your progress is tracked and writing submissions are graded by AI.
        </p>
      </div>

      {/* Practice type cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {cards.map((card) => {
          const Icon = card.icon
          return (
            <Link
              key={card.type}
              to={card.comingSoon ? '#' : `/practice/${card.type}`}
              onClick={card.comingSoon ? (e) => e.preventDefault() : undefined}
              className={`group bg-white rounded-xl border border-gray-200 p-6 transition-all duration-200 ${card.hover} hover:shadow-md ${card.comingSoon ? 'opacity-60 pointer-events-none' : ''}`}
            >
              <div className={`inline-flex items-center justify-center w-12 h-12 rounded-xl ${card.color} mb-4`}>
                <Icon className="w-6 h-6" />
              </div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">{card.title}</h2>
              <p className="text-sm text-gray-500 leading-relaxed">{card.description}</p>
              <span className="inline-block mt-4 text-sm font-medium text-green-600 group-hover:text-green-700">
                {card.comingSoon ? 'Coming Soon' : 'Start practice →'}
              </span>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
