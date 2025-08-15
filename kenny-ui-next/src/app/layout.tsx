import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { ThemeProvider } from '@/components/providers/theme-provider'
import { QueryProvider } from '@/components/providers/query-provider'
import { ToastProvider } from '@/components/providers/toast-provider'
import { CommandPalette } from '@/components/command-palette'
import { Analytics } from '@/components/analytics'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Kenny v2 - Local Multi-Agent Assistant',
  description: 'Privacy-first, local-first AI assistant with multi-agent workflows',
  icons: {
    icon: '/kenny-logo.svg',
  },
  viewport: 'width=device-width, initial-scale=1, maximum-scale=1',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} antialiased`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
        >
          <QueryProvider>
            <ToastProvider>
              <div className="min-h-screen bg-gradient-to-br from-kenny-gray-950 via-kenny-gray-900 to-kenny-gray-950">
                {children}
                <CommandPalette />
                <Analytics />
              </div>
            </ToastProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}