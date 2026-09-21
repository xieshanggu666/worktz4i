import React, { useState } from 'react'
import { api, handleActError } from '../api'
import { useStore } from '../store'

const MODE_LABEL = { accompany: '随行', rest: '休整' }

// 伙伴名册：商店招募的伙伴在此切换随行/休整；负伤伙伴只能在休息节点治疗。
// - 随行：进入战斗并每回合协助；同一时间仅一名随行（切随行自动换下原随行）。
// - 休整：保留在名册但不参战。
// - 负伤（hp<上限）：暂停参战，休息节点显示治疗按钮（每节点一次）。
// 切换/治疗都走普通 act（request_id 幂等、expected_rev 冲突 409）。
export default function CompanionPanel() {
  const view = useStore((s) => s.view)
  const runId = useStore((s) => s.runId)
  const applyRun = useStore((s) => s.applyRun)
  const [busyId, setBusyId] = useState(null)
  const [err, setErr] = useState('')

  const companions = view?.companions || []
  if (!view || companions.length === 0) return null
  const inBattle = !!view.in_battle
  const canHeal = view.rest_companion_heal_available === true

  async function send(cid, body) {
    setBusyId(cid); setErr('')
    try {
      const res = await api.act(runId, body)
      applyRun(res.run)
    } catch (e) {
      setErr(await handleActError(e, runId, applyRun))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="panellist companions-roster">
      <h3>🐾 伙伴</h3>
      {companions.map((c) => (
        <div key={c.id} className={`companion-card ${c.mode} ${c.wounded ? 'wounded' : ''}`}>
          <div className="cp-head">
            <b>{c.icon} {c.name}</b>
            <span className={`cp-mode ${c.mode}`}>
              {c.wounded ? '🩹 负伤' : MODE_LABEL[c.mode] || c.mode}
            </span>
          </div>
          <div className="cp-title">{c.title}</div>
          <div className="cp-hp" title="生命值：归零即负伤暂停参战，休息节点可治疗">
            生命 {c.hp}/{c.max_hp}
            <span className="cp-hearts">
              {Array.from({ length: c.max_hp }).map((_, i) => (
                <i key={i} className={i < c.hp ? 'full' : 'empty'}>♥</i>
              ))}
            </span>
          </div>
          <div className="cp-desc">{c.desc}</div>
          <div className="cp-actions">
            {c.wounded ? (
              <button className="primary cp-heal"
                      disabled={inBattle || !canHeal || busyId === c.id}
                      title={inBattle ? '战斗中无法治疗'
                        : canHeal ? '在休息节点治疗（回满并随行）' : '需要到休息节点才能治疗'}
                      onClick={() => send(c.id, { action: 'companion_heal', companion: c.id })}>
                {busyId === c.id ? '治疗中…' : '🩹 休息治疗'}
              </button>
            ) : (
              <>
                <button className={c.mode === 'accompany' ? 'primary' : ''}
                        disabled={inBattle || (c.mode === 'accompany') || busyId === c.id}
                        title={inBattle ? '战斗中无法调整' : '随行：进入战斗并每回合协助'}
                        onClick={() => send(c.id, {
                          action: 'companion_set_mode', companion: c.id, mode: 'accompany',
                        })}>
                  随行
                </button>
                <button className={c.mode === 'rest' ? 'primary' : ''}
                        disabled={inBattle || (c.mode === 'rest') || busyId === c.id}
                        title={inBattle ? '战斗中无法调整' : '休整：暂停参战'}
                        onClick={() => send(c.id, {
                          action: 'companion_set_mode', companion: c.id, mode: 'rest',
                        })}>
                  休整
                </button>
              </>
            )}
          </div>
        </div>
      ))}
      {err && <div className="error">{err}</div>}
    </div>
  )
}
