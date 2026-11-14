import { Link } from 'react-router-dom'

const entries = [
  {
    to: '/rooms',
    title: '找座位',
    desc: '按楼栋和时段查看空座，直接预约',
  },
]

export function Home() {
  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-200 bg-white p-6">
        <h1 className="text-lg font-semibold tracking-tight text-slate-900">今天去哪儿自习？</h1>
        <p className="mt-1 text-sm text-slate-500">
          先看看哪里有座，再决定坐哪儿。系统会在预约成功后提示你签到。
        </p>
      </section>

      <section className="grid gap-3 sm:grid-cols-2">
        {entries.map((entry) => (
          <Link
            key={entry.to}
            to={entry.to}
            className="rounded-xl border border-slate-200 bg-white p-5 transition-colors hover:border-slate-300"
          >
            <h2 className="text-sm font-medium text-slate-900">{entry.title}</h2>
            <p className="mt-1 text-sm text-slate-500">{entry.desc}</p>
          </Link>
        ))}

        <div className="rounded-xl border border-dashed border-slate-200 p-5">
          <h2 className="text-sm font-medium text-slate-400">我的预约</h2>
          <p className="mt-1 text-sm text-slate-400">M4 里程碑接入</p>
        </div>
      </section>
    </div>
  )
}