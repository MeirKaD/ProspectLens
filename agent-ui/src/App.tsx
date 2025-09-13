import { useState } from 'react'
import { Header } from '@/components/Header'
import { QualificationForm } from '@/components/QualificationForm'
import { ResultsPanel } from '@/components/ResultsPanel'
import { HeroSection } from '@/components/HeroSection'
import type { QualificationResult } from '@/types'

function App() {
  const [result, setResult] = useState<QualificationResult | null>(null)
  const [loading, setLoading] = useState(false)

  const handleQualification = (newResult: QualificationResult) => {
    setResult(newResult)
  }

  const handleLoadingChange = (isLoading: boolean) => {
    setLoading(isLoading)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-gray-100 dark:from-slate-950 dark:to-gray-900">
      <div className="container mx-auto px-4 py-6 max-w-7xl">
        <Header />

        {!result && !loading ? (
          <>
            <HeroSection />
            <div className="mt-16">
              <QualificationForm
                onResult={handleQualification}
                onLoadingChange={handleLoadingChange}
              />
            </div>
          </>
        ) : (
          <div className="mt-8">
            <ResultsPanel
              result={result}
              loading={loading}
              onReset={() => {
                setResult(null)
                setLoading(false)
              }}
            />
          </div>
        )}
      </div>
    </div>
  )
}

export default App