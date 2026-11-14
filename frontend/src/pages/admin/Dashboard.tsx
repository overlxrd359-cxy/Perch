const stats = [
  { label: '今日预约', value: '—' },
  { label: '当前在座', value: '—' },
  { label: '违约率', value: '—' },
]

export function Dashboard() {
  return (
    <div className="space-y-6">
      <div className="flex items-baseline justify-between">
        <h1 className="text-lg font-semibold tracking-tight text-slate-900">仪表盘</h1>
        <span className="text-xs text-slate-400">M5 里程碑接入真实数据</span>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {stats.map((stat) => (
          <div key={stat.label} className="rounded-xl border border-slate-200 bg-white p-5">
            <p className="text-sm text-slate-500">{stat.label}</p>
            <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">
              {stat.value}
            </p>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-dashed border-slate-200 bg-white px-6 py-16 text-center">
        <p className="text-sm text-slate-500">趋势图在 M5 接入</p>
      </div>
    </div>
  )
}