import {
  RadarChart as RechartsRadar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'

export default function RadarChart({ data }) {
  // Transform criteria object into recharts format
  const chartData = Object.entries(data).map(([key, val]) => ({
    criterion: formatCriterion(key),
    band: val.band,
    fullMark: 9,
  }))

  return (
    <div className="w-full h-80">
      <ResponsiveContainer>
        <RechartsRadar data={chartData}>
          <PolarGrid stroke="#e5e7eb" />
          <PolarAngleAxis
            dataKey="criterion"
            tick={{ fill: '#6b7280', fontSize: 12 }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 9]}
            tick={{ fill: '#9ca3af', fontSize: 10 }}
            tickCount={5}
          />
          <Tooltip
            contentStyle={{
              background: '#fff',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              fontSize: '13px',
            }}
          />
          <Radar
            name="Band Score"
            dataKey="band"
            stroke="#16a34a"
            fill="#16a34a"
            fillOpacity={0.2}
            strokeWidth={2}
          />
        </RechartsRadar>
      </ResponsiveContainer>
    </div>
  )
}

const LABELS = {
  task_response: 'Task Response',
  coherence_cohesion: 'Coherence & Cohesion',
  lexical_resource: 'Lexical Resource',
  grammatical_range_accuracy: 'Grammar',
}

function formatCriterion(key) {
  return LABELS[key] || key
}
