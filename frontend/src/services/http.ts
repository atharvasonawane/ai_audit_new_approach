export interface HttpClient {
  get<T>(url: string): Promise<T>
}

export const httpClient: HttpClient = {
  async get<T>(url: string) {
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`)
    }
    return (await response.json()) as T
  },
}
