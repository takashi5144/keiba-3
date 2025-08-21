import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  // Handle root path
  if (request.nextUrl.pathname === '/') {
    return NextResponse.next()
  }
  
  // Check if the request is for a page that exists
  const validPaths = ['/', '/predictions', '/backtest', '/data', '/settings']
  const pathname = request.nextUrl.pathname
  
  // If it's a valid path or an API/static file, continue
  if (
    validPaths.includes(pathname) ||
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname.includes('.')
  ) {
    return NextResponse.next()
  }
  
  // Otherwise, rewrite to the home page
  return NextResponse.rewrite(new URL('/', request.url))
}

export const config = {
  matcher: '/((?!_next/static|_next/image|favicon.ico).*)',
}