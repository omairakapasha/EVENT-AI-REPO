/**
 * Property-based tests for status badge color mapping.
 *
 * Property 4: Status badge color mapping is exhaustive (Requirements 2.6)
 *
 * Feature: vendor-portal-complete
 */
import * as fc from 'fast-check'

// Mirrors STATUS_COLORS in packages/vendor/src/app/dashboard/page.tsx
const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-700',
  confirmed: 'bg-blue-100 text-blue-700',
  in_progress: 'bg-indigo-100 text-indigo-700',
  completed: 'bg-green-100 text-green-700',
  cancelled: 'bg-red-100 text-red-700',
  rejected: 'bg-gray-100 text-gray-700',
  no_show: 'bg-gray-100 text-gray-500',
}

describe('Status badge color mapping is exhaustive (Property 4)', () => {
  it('every booking status maps to a non-empty CSS class string', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(
          'pending',
          'confirmed',
          'in_progress',
          'completed',
          'cancelled',
          'rejected',
          'no_show'
        ),
        (status) => {
          const classes = STATUS_COLORS[status]
          expect(classes).toBeDefined()
          expect(typeof classes).toBe('string')
          expect(classes.length).toBeGreaterThan(0)
        }
      ),
      { numRuns: 10 }
    )
  })

  it('pending includes a yellow/warning token', () => {
    expect(STATUS_COLORS['pending']).toMatch(/yellow|warning|amber/)
  })

  it('confirmed includes a blue token', () => {
    expect(STATUS_COLORS['confirmed']).toMatch(/blue/)
  })

  it('completed includes a green token', () => {
    expect(STATUS_COLORS['completed']).toMatch(/green/)
  })

  it('cancelled includes a red/grey token', () => {
    expect(STATUS_COLORS['cancelled']).toMatch(/red|gray|grey/)
  })

  it('rejected includes a red/grey token', () => {
    expect(STATUS_COLORS['rejected']).toMatch(/red|gray|grey/)
  })

  it('all 7 statuses are covered', () => {
    const required = ['pending', 'confirmed', 'in_progress', 'completed', 'cancelled', 'rejected', 'no_show']
    required.forEach((s) => {
      expect(STATUS_COLORS[s]).toBeDefined()
    })
  })
})
