export function Rooms() {
  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between">
        <h1 className="text-lg font-semibold tracking-tight text-slate-900">找座位</h1>
        <span className="text-xs text-slate-400">M2 / M3 里程碑接入</span>
      </div>

      <div className="rounded-xl border border-dashed border-slate-200 bg-white px-6 py-16 text-center">
        <p className="text-sm text-slate-500">还没有自习室数据</p>
        <p className="mt-1 text-sm text-slate-400">
          管理员在后台录入楼栋与座位后，这里会显示实时座位图。
        </p>
      </div>
    </div>
  )
}