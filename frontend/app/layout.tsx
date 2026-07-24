import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Ask Your Data — NL to SQL',
  description: 'Convert natural language questions into SQL queries and get instant results.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body style={{ margin: 0, padding: 0 }}>
        {children}
      </body>
    </html>
  )
}
