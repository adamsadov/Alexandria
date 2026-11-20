import type { NextConfig } from 'next'

// Where Django runs. Every backend request goes through these rewrites so the
// browser only ever talks to this Next.js origin (one origin = the session
// cookie and CSRF token just work, and there is no CORS to configure).
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      // Django REST API. Django URLs end in "/", but `:path*` drops a trailing
      // slash, which makes Django redirect back here forever. Match the
      // slashed form first so it's forwarded unchanged.
      { source: '/api/:path*/', destination: `${BACKEND_URL}/api/:path*/` },
      { source: '/api/:path*', destination: `${BACKEND_URL}/api/:path*` },
      // django-allauth (login, sign-up, logout, email verification, password reset)
      { source: '/_allauth/:path*', destination: `${BACKEND_URL}/_allauth/:path*` },
      // Uploaded files (profile pictures, club images)
      { source: '/media/:path*', destination: `${BACKEND_URL}/media/:path*` },
    ]
  },

  // Django's API routes end in a slash; don't let Next strip it and redirect.
  skipTrailingSlashRedirect: true,

  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'covers.openlibrary.org' },
      { protocol: 'https', hostname: '**.amazonaws.com' },
      { protocol: 'https', hostname: '**.cloudinary.com' },
      { protocol: 'https', hostname: 'upload.wikimedia.org' },
      { protocol: 'http', hostname: 'localhost' },
      { protocol: 'https', hostname: 'via.placeholder.com' },
    ],
  },
}

export default nextConfig
