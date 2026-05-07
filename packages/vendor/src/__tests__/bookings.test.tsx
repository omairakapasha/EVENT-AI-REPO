import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import BookingsPage from '@/app/bookings/page'
import { useVendorBookings, useConfirmBooking, useRejectBooking } from '@/lib/hooks/use-vendor-bookings'

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn(), back: jest.fn() }),
  usePathname: () => '/bookings',
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
jest.mock('@/lib/hooks/use-vendor-bookings')

const mockUseVendorBookings = useVendorBookings as jest.MockedFunction<typeof useVendorBookings>
const mockUseConfirmBooking = useConfirmBooking as jest.MockedFunction<typeof useConfirmBooking>
const mockUseRejectBooking = useRejectBooking as jest.MockedFunction<typeof useRejectBooking>

const mockBookings = [
  { id: 'b1', vendor_id: 'v1', service_id: 's1', user_id: 'u1', event_date: '2025-08-15', event_name: null, status: 'pending' as const, total_price: 500, currency: 'USD', client_name: 'Alice Johnson', client_email: null, event_location: null, special_requirements: null, created_at: '2025-07-01T10:00:00Z', updated_at: '2025-07-01T10:00:00Z' },
  { id: 'b2', vendor_id: 'v1', service_id: 's2', user_id: 'u2', event_date: '2025-08-10', event_name: null, status: 'confirmed' as const, total_price: 1200, currency: 'USD', client_name: 'Bob Smith', client_email: null, event_location: null, special_requirements: null, created_at: '2025-07-02T10:00:00Z', updated_at: '2025-07-02T10:00:00Z' },
]

function makeClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } })
}

function renderPage() {
  return render(<QueryClientProvider client={makeClient()}><BookingsPage /></QueryClientProvider>)
}

beforeEach(() => {
  mockUseConfirmBooking.mockReturnValue({ mutate: jest.fn(), isPending: false } as ReturnType<typeof useConfirmBooking>)
  mockUseRejectBooking.mockReturnValue({ mutateAsync: jest.fn(), isPending: false } as ReturnType<typeof useRejectBooking>)
})

describe('Bookings page', () => {
  it('renders filter tabs', async () => {
    mockUseVendorBookings.mockReturnValue({ data: { data: mockBookings, meta: { total: 2, page: 1, limit: 20, pages: 1 } }, isLoading: false, isError: false } as ReturnType<typeof useVendorBookings>)
    renderPage()
    await waitFor(() => expect(screen.getByText('All')).toBeInTheDocument())
    expect(screen.getAllByText('pending').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('confirmed').length).toBeGreaterThanOrEqual(1)
  })

  it('renders booking rows with client names', async () => {
    mockUseVendorBookings.mockReturnValue({ data: { data: mockBookings, meta: { total: 2, page: 1, limit: 20, pages: 1 } }, isLoading: false, isError: false } as ReturnType<typeof useVendorBookings>)
    renderPage()
    await waitFor(() => expect(screen.getByText('Alice Johnson')).toBeInTheDocument())
    expect(screen.getByText('Bob Smith')).toBeInTheDocument()
  })

  it('shows Confirm and Reject buttons for pending bookings', async () => {
    mockUseVendorBookings.mockReturnValue({ data: { data: mockBookings, meta: { total: 2, page: 1, limit: 20, pages: 1 } }, isLoading: false, isError: false } as ReturnType<typeof useVendorBookings>)
    renderPage()
    await waitFor(() => expect(screen.getByText('Confirm')).toBeInTheDocument())
    expect(screen.getByText('Reject')).toBeInTheDocument()
  })

  it('opens reject modal when Reject is clicked', async () => {
    mockUseVendorBookings.mockReturnValue({ data: { data: mockBookings, meta: { total: 2, page: 1, limit: 20, pages: 1 } }, isLoading: false, isError: false } as ReturnType<typeof useVendorBookings>)
    renderPage()
    await waitFor(() => expect(screen.getByText('Reject')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Reject'))
    await waitFor(() => expect(screen.getByText('Reject Booking')).toBeInTheDocument())
    expect(screen.getByPlaceholderText('Reason (optional)')).toBeInTheDocument()
  })

  it('shows empty state when no bookings', async () => {
    mockUseVendorBookings.mockReturnValue({ data: { data: [], meta: { total: 0, page: 1, limit: 20, pages: 0 } }, isLoading: false, isError: false } as ReturnType<typeof useVendorBookings>)
    renderPage()
    await waitFor(() => expect(screen.getByText('No bookings found')).toBeInTheDocument())
  })
})
