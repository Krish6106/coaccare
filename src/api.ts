const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  })
  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try { const body = await response.json(); detail = body.detail || detail } catch { /* response may not be JSON */ }
    throw new Error(detail)
  }
  return response.json() as Promise<T>
}

export const api = {
  dashboard: () => request<DashboardData>('/dashboard'),
  recurring: (query = '', category = 'All', severity = 'All', includeAll = false) => request<{items: DefectCluster[]; total: number}>(`/recurring-defects?q=${encodeURIComponent(query)}&category=${encodeURIComponent(category)}&severity=${encodeURIComponent(severity)}&include_all=${includeAll}`),
  detail: (id: string) => request<DefectCluster>(`/recurring-defects/${id}`),
  priorities: (query = '', priority = 'All', status = 'All') => request<{items: MaintenanceTask[]; total: number}>(`/priorities?q=${encodeURIComponent(query)}&priority=${encodeURIComponent(priority)}&status=${encodeURIComponent(status)}`),
  updatePriority: (id: number, payload: {status?: string; assigned_team?: string}) => request<MaintenanceTask>(`/priorities/${id}`, {method:'PATCH',body:JSON.stringify(payload)}),
  verifications: (status = 'All', query = '') => request<{items: RepairItem[]; total: number}>(`/verification?status=${encodeURIComponent(status)}&q=${encodeURIComponent(query)}`),
  verify: (id: number, outcome: string, notes: string) => request(`/verification/${id}`, {method:'POST',body:JSON.stringify({outcome,notes})}),
  notifications: () => request<{items: NotificationItem[]; unread: number}>('/notifications'),
  search: (query: string) => request<{items: SearchItem[]}>(`/search?q=${encodeURIComponent(query)}`),
  createDefect: (payload: Record<string,string>) => request('/defects', {method:'POST',body:JSON.stringify(payload)}),
}

export type DefectEvent = { id: number; coach_id: string; service: string; category: string; location: string; description: string; severity: string; source: string; reported_at: string; status: string; work_order_id?: string | null; recurrence_count: number; last_repair?: string | null; repair_summary?: string | null; verification_status?: string | null }
export type DefectCluster = DefectEvent & { record_count: number; repair_count: number; first_reported: string; recommended_action?: string; history: DefectEvent[] }
export type MaintenanceTask = { id: number; task_code: string; defect_id: number; coach_id: string; service: string; category: string; location: string; description: string; severity: string; priority: string; status: string; assigned_team: string; resource_status: string; due_date: string; recurrence_count: number; recommended_action: string }
export type RepairItem = { id:number; defect_id:number; work_order_id:string; coach_id:string; service:string; category:string; location:string; repair_summary:string; technician:string; repaired_at:string; verification_status:string; verified_at?:string|null; verification_notes?:string|null }
export type NotificationItem = {id:number;title:string;detail:string;kind:string;created_at:string;read:boolean}
export type SearchItem = {id:number;label:string;detail:string;type:string;path:string}
export type DashboardData = { metrics:{total_defect_records:number;recurring_defects:number;high_priority_tasks:number;awaiting_verification:number;period_comparison:{records_current:number;records_previous:number;recurring_current:number;recurring_previous:number}}; recurring_by_category:{category:string;count:number}[]; trend:{date:string;reports:number;recurring:number}[]; priority_distribution:{priority:string;count:number}[]; activity:{id:string;type:string;title:string;detail:string;at:string;tone:string}[]; attention:DefectCluster[] }
