/**
 * 管理端仪表盘。M5 接统计数据与 Recharts 图表，M0 只验证布局。
 */
export function Dashboard() {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-900">仪表盘</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {['今日预约', '当前在座', '上座率', '违约率'].map((label) => (
          <div key={label} className="rounded-xl border border-slate-200 bg-white p-5">
            <p className="text-sm text-slate-500">{label}</p>
            <p className="mt-2 text-2xl font-semibold text-slate-300">--</p>
            <p className="mt-1 text-xs text-slate-400">M5 接统计接口</p>
          </div>
        ))}
      </div>
    </div>
  )
}