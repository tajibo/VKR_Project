// next.config.js

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'Cache-Control', value: 'no-store, max-age=0' }
        ]
      }
    ]
  },

  async rewrites() {
    return [
      {
        source: '/api/:path*',
        // Проксирование на локальный FastAPI
        destination: 'http://localhost:8000/:path*',
      }
    ]
  },
}

module.exports = nextConfig;
