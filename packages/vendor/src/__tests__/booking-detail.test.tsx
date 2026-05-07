import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import BookingDetailPage from '@/app/bookings/[id]/page'
import { useBookingDetail, useBookingMessages, useSendMessage } from '@/lib/hooks/use-booking-detail'

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn(), back: jest.fn() }),
  usePathname: () => '/bookings/b1',
  useParams: () => ({ id: 'b1' }),
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
jest.mock('@/lib/hooks/use-booking-detail')

const mockUseBookingDetail = useBookingDetail as jest.MockedFunction<typeof useBookingDetail>
const mockUseBookingMessages = useBookingMessages as jest.MockedFunction<typeof useBookingMessages>
const mockUseSendMessage = useSendMessage as jest.MockedFunction<typeof useSendMessage>

const mockBooking = {
  id: 'b1', vendor_id: 'vendor-1', service_id: 's1', user_id: 'u1',
  event_date: '2025-08-15', event_name: null, status: 'confirmed' as const,
  total_price: 500, currency: 'USD', client_name: 'Alice Johnson',
  client_email: null, event_location: { city: 'Karachi', country: 'Pakistan' },
  special_requirements: null, created_at: '2025-07-01T10:00:00Z', updated_at: '2025-07-01T10:00:00Z',
}

const mockMessages = [
  { id: 'm1', booking_id: 'b1', sender_id: 'u1', sender_type: 'client' as const, message: 'Hello vendor!', attachments: [], is_read: true, created_at: '2025-07-01T10:00:00Z' },
  { id: 'm2', booking_id: 'b1', sender_id: 'vendor-1', sender_type: 'vendor' as const, message: 'Hello client!', attachments: [], is_read: true, created_at: '2025-07-01T11:00:00Z' },
]

function makeClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } })
}

function renderPage() {
  return render(<QueryClientProvider client={makeClient()}><BookingDetailPage /></QueryClientProvider>)
}

beforeEach(() => {
  mockUseSendMessage.mockReturnValue({ mutateAsync: jest.fn(), isPending: false } as ReturnType<typeof useSendMessage>)
})

describe('Booking Detail page', () => {
  it('renders booking fields correctly', async () => {
    mockUseBookingDetail.mockReturnValue({ data: mockBooking, isLoading: false } as ReturnType<typeof useBookingDetail>)
    mockUseBookingMessages.mockReturnValue({ data: mockMessages, isLoading: false } as ReturnType<typeof useBookingMessages>)
    renderPage()
    await waitFor(() => expect(screen.getByText('Alice Johnson')).toBeInTheDocument())
    expect(screen.getByText('Booking Details')).toBeInTheDocument()
  })

  it('renders messages from both parties', async () => {
    mockUseBookingDetail.mockReturnValue({ data: mockBooking, isLoading: false } as ReturnType<typeof useBookingDetail>)
    mockUseBookingMessages.mockReturnValue({ data: mockMessages, isLoading: false } as ReturnType<typeof useBookingMessages>)
    renderPage()
    await waitFor(() => expect(screen.getByText('Hello vendor!')).toBeInTheDocument())
    expect(screen.getByText('Hello client!')).toBeInTheDocument()
  })

  it('renders message input and Send button', async () => {
    mockUseBookingDetail.mockReturnValue({ data: mockBooking, isLoading: false } as ReturnType<typeof useBookingDetail>)
    mockUseBookingMessages.mockReturnValue({ data: [], isLoading: false } as ReturnType<typeof useBookingMessages>)
    renderPage()
    await waitFor(() => expect(screen.getByPlaceholderText('Type a message…')).toBeInTheDocument())
    expect(screen.getByText('Send')).toBeInTheDocument()
  })

  it('Send button is disabled when input is empty', async () => {
    mockUseBookingDetail.mockReturnValue({ data: mockBooking, isLoading: false } as ReturnType<typeof useBookingDetail>)
    mockUseBookingMessages.mockReturnValue({ data: [], isLoading: false } as ReturnType<typeof useBookingMessages>)
    renderPage()
    await waitFor(() => expect(screen.getByText('Send')).toBeInTheDocument())
    expect(screen.getByText('Send').closest('button')).toBeDisabled()
  })
})
