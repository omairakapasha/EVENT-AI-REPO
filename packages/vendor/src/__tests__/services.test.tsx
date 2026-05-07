import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ServicesPage from '@/app/services/page'
import { useVendorServices, useDeleteService } from '@/lib/hooks/use-vendor-services'

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
  usePathname: () => '/services',
}))
jest.mock('next/link', () => {
  const Link = ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a>
  Link.displayName = 'Link'
  return Link
})
jest.mock('@/lib/auth-store', () => ({
  useAuthStore: jest.fn(() => ({
    isAuthenticated: true,
    vendor: { id: 'vendor-1', businessName: 'Elite Events', status: 'ACTIVE', categories: [] },
    user: { id: 'u1', email: 'v@test.com', firstName: 'Test', lastName: 'Vendor', role: 'vendor' },
    logout: jest.fn(),
  })),
}))
jest.mock('@/components/vendor-layout', () => ({
  VendorLayout: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))
jest.mock('@/lib/hooks/use-vendor-services')

const mockUseVendorServices = useVendorServices as jest.MockedFunction<typeof useVendorServices>
const mockUseDeleteService = useDeleteService as jest.MockedFunction<typeof useDeleteService>

const mockServices = [
  { id: 's1', vendor_id: 'v1', name: 'Photography Package', description: 'Pro photography', price_min: 300, price_max: 800, capacity: 1, is_active: true, requirements: null, created_at: '2025-01-01T00:00:00Z', updated_at: '2025-01-01T00:00:00Z' },
  { id: 's2', vendor_id: 'v1', name: 'Catering Service', description: 'Full catering', price_min: 1000, price_max: 5000, capacity: 500, is_active: true, requirements: null, created_at: '2025-01-02T00:00:00Z', updated_at: '2025-01-02T00:00:00Z' },
]

function makeClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } })
}

function renderPage() {
  return render(<QueryClientProvider client={makeClient()}><ServicesPage /></QueryClientProvider>)
}

beforeEach(() => {
  mockUseDeleteService.mockReturnValue({ mutateAsync: jest.fn(), isPending: false } as ReturnType<typeof useDeleteService>)
})

describe('Services page', () => {
  it('renders services table with service names', async () => {
    mockUseVendorServices.mockReturnValue({ data: { data: mockServices, meta: { total: 2, pages: 1 } }, isLoading: false, isError: false } as ReturnType<typeof useVendorServices>)
    renderPage()
    await waitFor(() => expect(screen.getByText('Photography Package')).toBeInTheDocument())
    expect(screen.getByText('Catering Service')).toBeInTheDocument()
  })

  it('renders table column headers', async () => {
    mockUseVendorServices.mockReturnValue({ data: { data: mockServices, meta: { total: 2, pages: 1 } }, isLoading: false, isError: false } as ReturnType<typeof useVendorServices>)
    renderPage()
    await waitFor(() => expect(screen.getByText('Name')).toBeInTheDocument())
    expect(screen.getByText('Status')).toBeInTheDocument()
    expect(screen.getByText('Capacity')).toBeInTheDocument()
  })

  it('shows Add Service button', async () => {
    mockUseVendorServices.mockReturnValue({ data: { data: mockServices, meta: { total: 2, pages: 1 } }, isLoading: false, isError: false } as ReturnType<typeof useVendorServices>)
    renderPage()
    await waitFor(() => expect(screen.getByText('Add Service')).toBeInTheDocument())
  })

  it('shows empty state when no services', async () => {
    mockUseVendorServices.mockReturnValue({ data: { data: [], meta: { total: 0, pages: 0 } }, isLoading: false, isError: false } as ReturnType<typeof useVendorServices>)
    renderPage()
    await waitFor(() => expect(screen.getByText('No services yet')).toBeInTheDocument())
  })
})
