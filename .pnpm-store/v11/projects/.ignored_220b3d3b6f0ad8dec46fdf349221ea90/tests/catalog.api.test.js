import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../src/api/http.js', () => ({
  http: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

const { http } = await import('../src/api/http.js')
const { catalogApi } = await import('../src/api/catalog.api.js')

describe('catalogApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('unwraps paginated results', async () => {
    http.get.mockResolvedValue({ data: { results: [{ id: 1 }, { id: 2 }] } })
    await expect(catalogApi.listCategories()).resolves.toEqual([{ id: 1 }, { id: 2 }])
    expect(http.get).toHaveBeenCalledWith('/categories/', { params: { page_size: 200 } })
  })

  it('unwraps plain arrays', async () => {
    http.get.mockResolvedValue({ data: [{ id: 3 }] })
    await expect(catalogApi.listCategories()).resolves.toEqual([{ id: 3 }])
  })

  it('returns an empty list for unexpected payloads', async () => {
    http.get.mockResolvedValue({ data: { detail: 'error' } })
    await expect(catalogApi.listCategories()).resolves.toEqual([])
  })
})
