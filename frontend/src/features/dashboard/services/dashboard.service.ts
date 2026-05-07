import {
  complexitySummary,
  dashboardDefects,
  dashboardKpis,
  dashboardTrends,
  scanMetadata,
} from '../../../mock/dashboard.mock'

export const dashboardService = {
  async getKpis() {
    return Promise.resolve(dashboardKpis)
  },
  async getDefects() {
    return Promise.resolve(dashboardDefects)
  },
  async getTrends() {
    return Promise.resolve(dashboardTrends)
  },
  async getScanMetadata() {
    return Promise.resolve(scanMetadata)
  },
  async getComplexitySummary() {
    return Promise.resolve(complexitySummary)
  },
}
