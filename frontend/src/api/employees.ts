import { apiClient } from './client'
import type { Employee, EmployeeCreate, PaginatedResponse, Department, Designation } from '../types'

interface EmployeeFilters {
  page?: number
  page_size?: number
  search?: string
  department_id?: number
  status?: string
  sort_by?: string
  sort_dir?: 'asc' | 'desc'
}

export const employeesApi = {
  list: async (filters: EmployeeFilters = {}): Promise<PaginatedResponse<Employee>> => {
    const params = new URLSearchParams()
    if (filters.page) params.set('page', String(filters.page))
    if (filters.page_size) params.set('page_size', String(filters.page_size))
    if (filters.search) params.set('search', filters.search)
    if (filters.department_id) params.set('department_id', String(filters.department_id))
    if (filters.status) params.set('status', filters.status)
    if (filters.sort_by) params.set('sort_by', filters.sort_by)
    if (filters.sort_dir) params.set('sort_dir', filters.sort_dir)
    const { data } = await apiClient.get<PaginatedResponse<Employee>>(`/employees?${params}`)
    return data
  },

  get: async (id: number): Promise<Employee> => {
    const { data } = await apiClient.get<Employee>(`/employees/${id}`)
    return data
  },

  create: async (payload: EmployeeCreate): Promise<Employee> => {
    const { data } = await apiClient.post<Employee>('/employees', payload)
    return data
  },

  update: async (id: number, payload: Partial<EmployeeCreate>): Promise<Employee> => {
    const { data } = await apiClient.put<Employee>(`/employees/${id}`, payload)
    return data
  },

  deactivate: async (id: number): Promise<void> => {
    await apiClient.delete(`/employees/${id}`)
  },
}

export const departmentsApi = {
  list: async (): Promise<PaginatedResponse<Department>> => {
    const { data } = await apiClient.get<PaginatedResponse<Department>>('/departments?page_size=100')
    return data
  },

  getDesignations: async (deptId: number): Promise<Designation[]> => {
    const { data } = await apiClient.get<Designation[]>(`/departments/${deptId}/designations`)
    return data
  },
}
