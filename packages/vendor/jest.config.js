const nextJest = require('next/jest')

const createJestConfig = nextJest({ dir: './' })

/** @type {import('jest').Config} */
const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  testMatch: [
    '**/__tests__/**/*.test.{ts,tsx}',
    '**/__tests__/**/*.property.test.{ts,tsx}',
  ],
  transformIgnorePatterns: [
    '/node_modules/(?!(msw|@mswjs|rettime|@bundled-es-modules)/)',
  ],
}

module.exports = createJestConfig(customJestConfig)
