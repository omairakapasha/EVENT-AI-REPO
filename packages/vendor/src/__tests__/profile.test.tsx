import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ProfilePage from '@/app/profile/page'
import { useVendorProfile, useUpdateProfile } from '@/lib/hooks/use-vendor-profile'

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
  usePathname: () => '/profile',
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
jest.mock('@/lib/hooks/use-vendor-profile')

const mockUseVendorProfile = useVendorProfile as jest.MockedFunction<typeof useVendorProfile>
const mockUseUpdateProfile = useUpdateProfile as jest.MockedFunction<typeof useUpdateProfile>

const mockVendor = {
  id: 'vendor-1', userId: 'u1', businessName: 'Elite Events Co.',
  description: 'Premium event services', contactEmail: 'contact@elite.pk',
  contactPhone: '+92-300-1234567', website: 'https://elite.pk',
  logoUrl: null, city: 'Karachi', region: 'Sindh', status: 'ACTIVE' as const,
  rating: 4.8, totalReviews: 127, categories: [],
}

function makeClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } })
}

function renderPage() {
  return render(<QueryClientProvider client={makeClient()}><ProfilePage /></QueryClientProvider>)
}

beforeEach(() => {
  mockUseUpdateProfile.mockReturnValue({ mutateAsync: jest.fn(), isPending: false } as ReturnType<typeof useUpdateProfile>)
})

describe('Profile page', () => {
  it('renders form fields pre-populated with profile data', async () => {
    mockUseVendorProfile.mockReturnValue({ data: mockVendor, isLoading: false } as ReturnType<typeof useVendorProfile>)
    renderPage()
    await waitFor(() => expect(screen.getByDisplayValue('Elite Events Co.')).toBeInTheDocument())
    expect(screen.getByDisplayValue('contact@elite.pk')).toBeInTheDocument()
  })

  it('shows the ACTIVE status badge', async () => {
    mockUseVendorProfile.mockReturnValue({ data: mockVendor, isLoading: false } as ReturnType<typeof useVendorProfile>)
    renderPage()
    await waitFor(() => expect(screen.getByText('ACTIVE')).toBeInTheDocument())
  })

  it('shows Edit Profile button when not editing', async () => {
    mockUseVendorProfile.mockReturnValue({ data: mockVendor, isLoading: false } as ReturnType<typeof useVendorProfile>)
    renderPage()
    await waitFor(() => expect(screen.getByText('Edit Profile')).toBeInTheDocument())
  })

  it('shows Cancel and Save Changes buttons after clicking Edit Profile', async () => {
    mockUseVendorProfile.mockReturnValue({ data: mockVendor, isLoading: false } as ReturnType<typeof useVendorProfile>)
    renderPage()
    await waitFor(() => expect(screen.getByText('Edit Profile')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Edit Profile'))
    await waitFor(() => expect(screen.getByText('Cancel')).toBeInTheDocument())
    expect(screen.getByText('Save Changes')).toBeInTheDocument()
  })

  it('shows validation error for empty business name', async () => {
    mockUseVendorProfile.mockReturnValue({ data: mockVendor, isLoading: false } as ReturnType<typeof useVendorProfile>)
    renderPage()
    await waitFor(() => expect(screen.getByText('Edit Profile')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Edit Profile'))
    await waitFor(() => expect(screen.getByText('Save Changes')).toBeInTheDocument())
    const nameInput = screen.getByDisplayValue('Elite Events Co.')
    fireEvent.change(nameInput, { target: { value: '' } })
    fireEvent.click(screen.getByText('Save Changes'))
    await waitFor(() => expect(screen.getByText('Business name is required')).toBeInTheDocument())
  })

  it('shows validation error for invalid website URL', async () => {
    mockUseVendorProfile.mockReturnValue({ data: mockVendor, isLoading: false } as ReturnType<typeof useVendorProfile>)
    renderPage()
    await waitFor(() => expect(screen.getByText('Edit Profile')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Edit Profile'))
    await waitFor(() => expect(screen.getByText('Save Changes')).toBeInTheDocument())
    const websiteInput = screen.getByDisplayValue('https://elite.pk')
    fireEvent.change(websiteInput, { target: { value: 'not-a-url' } })
    fireEvent.click(screen.getByText('Save Changes'))
    await waitFor(() => expect(screen.getByText('Website must start with http:// or https://')).toBeInTheDocument())
  })
})
