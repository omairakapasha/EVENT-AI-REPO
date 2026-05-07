/**
 * Property-based tests for auth-store mapping helpers.
 *
 * Property 1: _mapUser is a total function (Requirements 1.2)
 * Property 2: _mapVendor is a total function (Requirements 1.3)
 *
 * Feature: vendor-portal-complete
 */
import * as fc from 'fast-check'
import { _mapUser, _mapVendor } from '../lib/auth-store'

// ── Property 1: _mapUser field mapping ───────────────────────────────────────

describe('_mapUser field mapping (Property 1)', () => {
  it('maps snake_case user fields to camelCase for any valid input', () => {
    fc.assert(
      fc.property(
        fc.record({
          id: fc.string({ minLength: 1 }),
          email: fc.string({ minLength: 1 }),
          first_name: fc.option(fc.string(), { nil: null }),
          last_name: fc.option(fc.string(), { nil: null }),
          email_verified: fc.boolean(),
          role: fc.constantFrom('user', 'vendor', 'admin'),
        }),
        (input) => {
          const result = _mapUser(input as Record<string, unknown>)
          expect(result.firstName).toBe(input.first_name)
          expect(result.lastName).toBe(input.last_name)
          expect(result.emailVerified).toBe(input.email_verified)
          expect(result.id).toBe(input.id)
          expect(result.email).toBe(input.email)
        }
      ),
      { numRuns: 25 }
    )
  })

  it('always returns a valid User shape regardless of input values', () => {
    fc.assert(
      fc.property(
        fc.record({
          id: fc.string({ minLength: 1 }),
          email: fc.string({ minLength: 1 }),
          first_name: fc.option(fc.string(), { nil: null }),
          last_name: fc.option(fc.string(), { nil: null }),
          email_verified: fc.boolean(),
          role: fc.constantFrom('user', 'vendor', 'admin'),
        }),
        (input) => {
          const result = _mapUser(input as Record<string, unknown>)
          // Result must always have all required User fields
          expect(typeof result.id).toBe('string')
          expect(typeof result.email).toBe('string')
          expect(typeof result.emailVerified).toBe('boolean')
          expect(['user', 'vendor', 'admin']).toContain(result.role)
        }
      ),
      { numRuns: 25 }
    )
  })
})

// ── Property 2: _mapVendor field mapping ─────────────────────────────────────

describe('_mapVendor field mapping (Property 2)', () => {
  it('maps snake_case vendor fields to camelCase for any valid input', () => {
    fc.assert(
      fc.property(
        fc.record({
          id: fc.string({ minLength: 1 }),
          user_id: fc.string({ minLength: 1 }),
          business_name: fc.string({ minLength: 1 }),
          contact_email: fc.string({ minLength: 1 }),
          status: fc.constantFrom('PENDING', 'ACTIVE', 'SUSPENDED', 'REJECTED'),
          rating: fc.float({ min: 0, max: 5, noNaN: true }),
          total_reviews: fc.nat(),
        }),
        (input) => {
          const result = _mapVendor(input as Record<string, unknown>)
          expect(result.businessName).toBe(input.business_name)
          expect(result.contactEmail).toBe(input.contact_email)
          expect(result.userId).toBe(input.user_id)
          expect(result.id).toBe(input.id)
        }
      ),
      { numRuns: 25 }
    )
  })

  it('status is always one of the four valid values', () => {
    fc.assert(
      fc.property(
        fc.record({
          id: fc.string({ minLength: 1 }),
          user_id: fc.string({ minLength: 1 }),
          business_name: fc.string({ minLength: 1 }),
          contact_email: fc.string({ minLength: 1 }),
          status: fc.constantFrom('PENDING', 'ACTIVE', 'SUSPENDED', 'REJECTED'),
          rating: fc.float({ min: 0, max: 5, noNaN: true }),
          total_reviews: fc.nat(),
        }),
        (input) => {
          const result = _mapVendor(input as Record<string, unknown>)
          expect(['PENDING', 'ACTIVE', 'SUSPENDED', 'REJECTED']).toContain(result.status)
        }
      ),
      { numRuns: 25 }
    )
  })
})
