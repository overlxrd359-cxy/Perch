/**
 * 找座位页。M2 接楼栋/自习室列表，M3 接座位图与预约弹窗。
 */
export function Rooms() {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center">
      <h2 className="text-base font-medium text-slate-900">座位图还没接</h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
        这里在 M2 之后会显示楼栋 → 自习室 → 座位图。现在能看到这个页面，说明前端路由与布局已经跑通。
      </p>
    </div>
  )
}