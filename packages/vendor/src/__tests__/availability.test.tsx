import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AvailabilityPage from '@/app/availability/page'
import { useVendorAvailability, useUpsertAvailability } from '@/lib/hooks/use-vendor-availability'

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
  usePathname: () => '/availability',
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
jest.mock('@/lib/hooks/use-vendor-availability')

const mockUseVendorAvailability = useVendorAvailability as jest.MockedFunction<typeof useVendorAvailability>
const mockUseUpsertAvailability = useUpsertAvailability as jest.MockedFunction<typeof useUpsertAvailability>

const today = new Date()
const year = today.getFullYear()
const month = String(today.getMonth() + 1).padStart(2, '0')

const mockAvailability = [
  { id: 'a1', vendor_id: 'v1', service_id: null, date: `${year}-${month}-10`, status: 'available' as const, notes: null, booking_id: null, created_at: '2025-07-01T00:00:00Z', updated_at: '2025-07-01T00:00:00Z' },
  { id: 'a2', vendor_id: 'v1', service_id: null, date: `${year}-${month}-15`, status: 'blocked' as const, notes: null, booking_id: null, created_at: '2025-07-01T00:00:00Z', updated_at: '2025-07-01T00:00:00Z' },
]

function makeClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } })
}

function renderPage() {
  return render(<QueryClientProvider client={makeClient()}><AvailabilityPage /></QueryClientProvider>)
}

beforeEach(() => {
  mockUseUpsertAvailability.mockReturnValue({ mutateAsync: jest.fn(), isPending: false } as ReturnType<typeof useUpsertAvailability>)
})

describe('Availability page', () => {
  it('renders the Availability heading', async () => {
    mockUseVendorAvailability.mockReturnValue({ data: mockAvailability, isLoading: false } as ReturnType<typeof useVendorAvailability>)
    renderPage()
    await waitFor(() => expect(screen.getByText('Availability')).toBeInTheDocument())
  })

  it('renders the calendar grid with day headers', async () => {
    mockUseVendorAvailability.mockReturnValue({ data: mockAvailability, isLoading: false } as ReturnType<typeof useVendorAvailability>)
    renderPage()
    await waitFor(() => expect(screen.getByText('Sun')).toBeInTheDocument())
    expect(screen.getByText('Mon')).toBeInTheDocument()
    expect(screen.getByText('Sat')).toBeInTheDocument()
  })

  it('renders the status legend', async () => {
    mockUseVendorAvailability.mockReturnValue({ data: mockAvailability, isLoading: false } as ReturnType<typeof useVendorAvailability>)
    renderPage()
    await waitFor(() => expect(screen.getByText('Available')).toBeInTheDocument())
    expect(screen.getByText('Blocked')).toBeInTheDocument()
    expect(screen.getByText('Booked')).toBeInTheDocument()
  })

  it('renders month navigation', async () => {
    mockUseVendorAvailability.mockReturnValue({ data: [], isLoading: false } as ReturnType<typeof useVendorAvailability>)
    renderPage()
    const monthNames = ['January','February','March','April','May','June','July','August','September','October','November','December']
    const currentMonth = monthNames[today.getMonth()]
    await waitFor(() => expect(screen.getByText(new RegExp(currentMonth))).toBeInTheDocument())
  })
})
