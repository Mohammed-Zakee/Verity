import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

export const metadata: Metadata = {
  title: 'Verity — Business Intelligence Scraper',
  description: 'AI-powered business scraper. Give Verity a company name and location — it extracts reviews, ratings, sentiment analysis, red flags, and competitive intelligence in real time.',
  keywords: ['business scraper', 'review analysis', 'sentiment analysis', 'Google Maps scraper', 'business intelligence'],
  openGraph: {
    title: 'Verity — Business Intelligence Scraper',
    description: 'Drop a business. We\'ll tell you everything.',
    type: 'website',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
      </head>
      <body className={inter.variable}>{children}</body>
    </html>
  )
}
