// Test for API client
import { ApiClient, ApiError } from '../api'

// Mock fetch
global.fetch = jest.fn()

describe('ApiClient', () => {
  let apiClient: ApiClient
  
  beforeEach(() => {
    apiClient = new ApiClient('http://localhost:3000')
    jest.clearAllMocks()
  })

  describe('successful requests', () => {
    it('makes GET requests correctly', async () => {
      const mockResponse = { data: 'test' }
      ;(fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: {
          get: (name: string) => name === 'content-type' ? 'application/json' : null,
        },
      })

      const result = await apiClient.get('/test')

      expect(fetch).toHaveBeenCalledWith('http://localhost:3000/test', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      expect(result).toEqual(mockResponse)
    })

    it('makes POST requests with data', async () => {
      const mockResponse = { success: true }
      const postData = { name: 'test' }
      
      ;(fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: {
          get: (name: string) => name === 'content-type' ? 'application/json' : null,
        },
      })

      const result = await apiClient.post('/test', postData)

      expect(fetch).toHaveBeenCalledWith('http://localhost:3000/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(postData),
      })
      expect(result).toEqual(mockResponse)
    })
  })

  describe('error handling', () => {
    it('throws ApiError for HTTP error responses', async () => {
      ;(fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 404,
        text: () => Promise.resolve('Not Found'),
      })

      await expect(apiClient.get('/test')).rejects.toThrow(ApiError)
      await expect(apiClient.get('/test')).rejects.toThrow('HTTP 404: Not Found')
    })

    it('throws ApiError for network errors', async () => {
      ;(fetch as jest.Mock).mockRejectedValue(new Error('Network Error'))

      await expect(apiClient.get('/test')).rejects.toThrow(ApiError)
      await expect(apiClient.get('/test')).rejects.toThrow('Network error: Network Error')
    })
  })

  describe('utility methods', () => {
    it('creates EventSource correctly', () => {
      const eventSource = apiClient.createEventSource('/stream')
      expect(eventSource).toBeInstanceOf(EventSource)
    })

    it('creates WebSocket correctly', () => {
      const webSocket = apiClient.createWebSocket('/ws')
      expect(webSocket).toBeInstanceOf(WebSocket)
    })
  })
})