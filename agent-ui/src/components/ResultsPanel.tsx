import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ArrowLeft, Brain, Search, Star, Clock, AlertCircle, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import type { QualificationResult } from '@/types'

interface ResultsPanelProps {
  result: QualificationResult | null
  loading: boolean
  onReset: () => void
}

const getScoreColor = (score: number) => {
  if (score >= 8) return 'text-green-600 dark:text-green-400'
  if (score >= 6) return 'text-blue-600 dark:text-blue-400'
  if (score >= 4) return 'text-yellow-600 dark:text-yellow-400'
  return 'text-red-600 dark:text-red-400'
}

const getScoreBgColor = (score: number) => {
  if (score >= 8) return 'bg-green-500/20 border-green-500/30'
  if (score >= 6) return 'bg-blue-500/20 border-blue-500/30'
  if (score >= 4) return 'bg-yellow-500/20 border-yellow-500/30'
  return 'bg-red-500/20 border-red-500/30'
}

const getScoreLabel = (score: number) => {
  if (score >= 8) return 'Highly Qualified'
  if (score >= 6) return 'Well Qualified'
  if (score >= 4) return 'Minimally Qualified'
  return 'Not Qualified'
}

export function ResultsPanel({ result, loading, onReset }: ResultsPanelProps) {
  if (loading) {
    return (
      <div className="max-w-4xl mx-auto">
        <Card className="p-12 bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm border-0 shadow-xl text-center">
          <div className="space-y-6">
            <div className="w-16 h-16 bg-gradient-to-br from-violet-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto">
              <Loader2 className="w-8 h-8 text-white animate-spin" />
            </div>
            <div>
              <h2 className="text-3xl font-bold mb-4">AI Analysis in Progress</h2>
              <p className="text-muted-foreground text-lg">
                Our advanced AI agent is researching and evaluating the candidate...
              </p>
            </div>
            <div className="flex justify-center">
              <div className="flex items-center space-x-8">
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-blue-400 rounded-full animate-pulse" />
                  <span className="text-sm text-muted-foreground">Searching web sources</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-purple-400 rounded-full animate-pulse animation-delay-300" />
                  <span className="text-sm text-muted-foreground">Analyzing qualifications</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse animation-delay-600" />
                  <span className="text-sm text-muted-foreground">Generating insights</span>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </div>
    )
  }

  if (!result) {
    return null
  }

  const score = result.qualification_score || 0
  const hasError = result.error

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header with back button */}
      <div className="flex items-center justify-between">
        <Button
          variant="ghost"
          onClick={onReset}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="w-4 h-4" />
          New Analysis
        </Button>
        <Badge variant="outline" className="flex items-center gap-2">
          <Clock className="w-4 h-4" />
          Completed {new Date(result.timestamp).toLocaleString()}
        </Badge>
      </div>

      {/* Main Results Card */}
      <Card className="p-8 bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm border-0 shadow-xl">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Score Section */}
          <div className="lg:col-span-1">
            <div className="text-center space-y-4">
              <div className={`w-32 h-32 rounded-full border-4 flex items-center justify-center mx-auto ${getScoreBgColor(score)}`}>
                <div className="text-center">
                  <div className={`text-4xl font-bold ${getScoreColor(score)}`}>
                    {hasError ? '!' : score}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {hasError ? 'Error' : '/ 10'}
                  </div>
                </div>
              </div>

              <div>
                <h3 className={`text-xl font-semibold ${getScoreColor(score)}`}>
                  {hasError ? 'Analysis Failed' : getScoreLabel(score)}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {hasError ? 'Check details below' : `Score: ${score}/10`}
                </p>
              </div>

              {!hasError && (
                <div className="flex justify-center space-x-1">
                  {[...Array(5)].map((_, i) => (
                    <Star
                      key={i}
                      className={`w-5 h-5 ${
                        i < Math.round(score / 2)
                          ? 'text-yellow-400 fill-yellow-400'
                          : 'text-gray-300'
                      }`}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Details Section */}
          <div className="lg:col-span-2 space-y-6">
            <div>
              <h2 className="text-2xl font-bold mb-4">
                {result.person_name}
              </h2>

              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="flex items-center gap-2">
                  <Search className="w-5 h-5 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">
                    {result.searches_performed || 0} searches performed
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Brain className="w-5 h-5 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">
                    AI-powered analysis
                  </span>
                </div>
              </div>
            </div>

            <Separator />

            <Tabs defaultValue="reasoning" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="reasoning" className="flex items-center gap-2">
                  <Brain className="w-4 h-4" />
                  Analysis
                </TabsTrigger>
                <TabsTrigger value="sources" className="flex items-center gap-2">
                  <Search className="w-4 h-4" />
                  Sources ({result.information_sources?.length || 0})
                </TabsTrigger>
                <TabsTrigger value="raw" className="flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  Raw Data
                </TabsTrigger>
              </TabsList>

              <TabsContent value="reasoning" className="mt-6">
                <div className="space-y-4">
                  <div className="p-6 rounded-lg bg-muted/50 border">
                    <div className="flex items-start gap-3">
                      {hasError ? (
                        <XCircle className="w-5 h-5 text-red-500 mt-1 flex-shrink-0" />
                      ) : (
                        <CheckCircle className="w-5 h-5 text-green-500 mt-1 flex-shrink-0" />
                      )}
                      <div className="flex-1">
                        <h4 className="font-medium mb-2">
                          {hasError ? 'Error Details' : 'Qualification Assessment'}
                        </h4>
                        <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                          {result.qualification_reasoning || 'No reasoning provided.'}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="sources" className="mt-6">
                <div className="space-y-4">
                  {result.information_sources && result.information_sources.length > 0 ? (
                    result.information_sources.map((source, index) => (
                      <Card key={index} className="p-4 bg-muted/30">
                        <div className="flex items-start gap-3">
                          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center text-white text-sm font-medium">
                            {index + 1}
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <Badge variant="outline" className="text-xs">
                                {source.source}
                              </Badge>
                              {source.found_existing && (
                                <Badge variant="secondary" className="text-xs">
                                  Existing Data
                                </Badge>
                              )}
                            </div>
                            <p className="text-sm text-muted-foreground">
                              Query: "{source.query}"
                            </p>
                          </div>
                        </div>
                      </Card>
                    ))
                  ) : (
                    <div className="text-center py-8 text-muted-foreground">
                      <Search className="w-12 h-12 mx-auto mb-4 opacity-50" />
                      <p>No information sources available</p>
                    </div>
                  )}
                </div>
              </TabsContent>

              <TabsContent value="raw" className="mt-6">
                <div className="p-4 bg-muted/30 rounded-lg">
                  <pre className="text-xs overflow-auto max-h-96">
                    {JSON.stringify(result, null, 2)}
                  </pre>
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </Card>
    </div>
  )
}