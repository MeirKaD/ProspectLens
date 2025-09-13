import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Plus, X, User, Calendar, Users, Presentation, Sparkles, Link, ToggleLeft, ToggleRight } from 'lucide-react'
import type { QualificationResult, EventDetails } from '@/types'

interface QualificationFormProps {
  onResult: (result: QualificationResult) => void
  onLoadingChange: (loading: boolean) => void
}

export function QualificationForm({ onResult, onLoadingChange }: QualificationFormProps) {
  const [personName, setPersonName] = useState('')
  const [eventUrl, setEventUrl] = useState('')
  const [useManualDetails, setUseManualDetails] = useState(false)
  const [eventDetails, setEventDetails] = useState<EventDetails>({
    name: '',
    type: '',
    requirements: [''],
    audience: '',
    format: ''
  })
  const [activeTab, setActiveTab] = useState('person')

  const addRequirement = () => {
    setEventDetails(prev => ({
      ...prev,
      requirements: [...prev.requirements, '']
    }))
  }

  const removeRequirement = (index: number) => {
    setEventDetails(prev => ({
      ...prev,
      requirements: prev.requirements.filter((_, i) => i !== index)
    }))
  }

  const updateRequirement = (index: number, value: string) => {
    setEventDetails(prev => ({
      ...prev,
      requirements: prev.requirements.map((req, i) => i === index ? value : req)
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!personName.trim()) {
      return
    }

    // Validate based on the method being used
    if (useManualDetails && !eventDetails.name.trim()) {
      return
    }
    if (!useManualDetails && !eventUrl.trim()) {
      return
    }

    onLoadingChange(true)

    try {
      let response;

      if (useManualDetails) {
        // Use manual event details
        response = await fetch('http://localhost:8000/qualify', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            person_name: personName,
            event_details: {
              ...eventDetails,
              requirements: eventDetails.requirements.filter(req => req.trim() !== '')
            }
          })
        })
      } else {
        // Use URL-based extraction (default)
        response = await fetch('http://localhost:8000/qualify-from-url', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            person_name: personName,
            event_url: eventUrl
          })
        })
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      onResult(result)
    } catch (error) {
      console.error('Error:', error)
      onResult({
        person_name: personName,
        qualification_score: 0,
        qualification_reasoning: `Error occurred: ${error instanceof Error ? error.message : 'Unknown error'}`,
        searches_performed: 0,
        information_sources: [],
        timestamp: new Date().toISOString(),
        error: error instanceof Error ? error.message : 'Unknown error'
      })
    } finally {
      onLoadingChange(false)
    }
  }

  const isFormValid = personName.trim() !== '' &&
    (useManualDetails ? eventDetails.name.trim() !== '' : eventUrl.trim() !== '')

  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold mb-4">Start Qualification Analysis</h2>
        <p className="text-muted-foreground">Fill in the details below to begin AI-powered candidate evaluation</p>
      </div>

      <Card className="p-8 bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm border-0 shadow-xl">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2 mb-8">
            <TabsTrigger value="person" className="flex items-center gap-2">
              <User className="w-4 h-4" />
              Person Details
            </TabsTrigger>
            <TabsTrigger value="event" className="flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              Event Details
            </TabsTrigger>
          </TabsList>

          <form onSubmit={handleSubmit}>
            <TabsContent value="person" className="space-y-6">
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium flex items-center gap-2">
                    <User className="w-4 h-4" />
                    Person Name
                  </label>
                  <Input
                    placeholder="e.g. John Smith from Google"
                    value={personName}
                    onChange={(e) => setPersonName(e.target.value)}
                    className="text-lg p-6 bg-white/50 dark:bg-slate-900/50"
                  />
                  <p className="text-sm text-muted-foreground">
                    Include company or title for better search results
                  </p>
                </div>

                <div className="flex justify-between items-center pt-6">
                  <Badge variant="outline" className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-blue-400 rounded-full" />
                    Step 1 of 2
                  </Badge>
                  <Button
                    type="button"
                    onClick={() => setActiveTab('event')}
                    disabled={!personName.trim()}
                    className="flex items-center gap-2"
                  >
                    Next: Event Details
                    <Sparkles className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="event" className="space-y-6">
              {/* Primary method: Event URL */}
              <div className="space-y-4">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                      <Link className="w-4 h-4 text-white" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold">Event URL (Recommended)</h3>
                      <p className="text-sm text-muted-foreground">AI will automatically extract event details from URL</p>
                    </div>
                  </div>
                  <Badge className="bg-gradient-to-r from-blue-500 to-purple-600 text-white">
                    ✨ Smart
                  </Badge>
                </div>

                {!useManualDetails && (
                  <div className="space-y-2">
                    <Input
                      placeholder="e.g. https://luma.com/event-url or https://eventbrite.com/event-url"
                      value={eventUrl}
                      onChange={(e) => setEventUrl(e.target.value)}
                      className="text-lg p-6 bg-white/50 dark:bg-slate-900/50"
                    />
                    <p className="text-sm text-muted-foreground">
                      Paste any event URL (Luma, Eventbrite, Meetup, etc.) for automatic extraction
                    </p>
                  </div>
                )}
              </div>

              <Separator />

              {/* Toggle for manual details */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setUseManualDetails(!useManualDetails)}
                    className="flex items-center gap-2"
                  >
                    {useManualDetails ? <ToggleRight className="w-5 h-5" /> : <ToggleLeft className="w-5 h-5" />}
                    Manual Event Details
                  </Button>
                </div>
                <Badge variant="outline" className="text-xs">
                  {useManualDetails ? 'Manual Mode' : 'Auto Mode'}
                </Badge>
              </div>

              {/* Manual event details (optional) */}
              {useManualDetails && (
                <>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 p-6 bg-muted/30 rounded-lg border border-dashed">
                    <div className="space-y-2">
                      <label className="text-sm font-medium flex items-center gap-2">
                        <Calendar className="w-4 h-4" />
                        Event Name
                      </label>
                      <Input
                        placeholder="e.g. AI/ML Conference 2024"
                        value={eventDetails.name}
                        onChange={(e) => setEventDetails(prev => ({ ...prev, name: e.target.value }))}
                        className="bg-white/50 dark:bg-slate-900/50"
                      />
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium">Event Type</label>
                      <Input
                        placeholder="e.g. Technical Conference"
                        value={eventDetails.type}
                        onChange={(e) => setEventDetails(prev => ({ ...prev, type: e.target.value }))}
                        className="bg-white/50 dark:bg-slate-900/50"
                      />
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium flex items-center gap-2">
                        <Users className="w-4 h-4" />
                        Target Audience
                      </label>
                      <Input
                        placeholder="e.g. ML engineers, data scientists"
                        value={eventDetails.audience}
                        onChange={(e) => setEventDetails(prev => ({ ...prev, audience: e.target.value }))}
                        className="bg-white/50 dark:bg-slate-900/50"
                      />
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium flex items-center gap-2">
                        <Presentation className="w-4 h-4" />
                        Format
                      </label>
                      <Input
                        placeholder="e.g. 45-minute presentation"
                        value={eventDetails.format}
                        onChange={(e) => setEventDetails(prev => ({ ...prev, format: e.target.value }))}
                        className="bg-white/50 dark:bg-slate-900/50"
                      />
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium">Requirements</label>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={addRequirement}
                        className="flex items-center gap-2"
                      >
                        <Plus className="w-4 h-4" />
                        Add Requirement
                      </Button>
                    </div>

                    <div className="space-y-3">
                      {eventDetails.requirements.map((req, index) => (
                        <div key={index} className="flex items-center gap-3">
                          <div className="flex-1">
                            <Textarea
                              placeholder={`Requirement ${index + 1}...`}
                              value={req}
                              onChange={(e) => updateRequirement(index, e.target.value)}
                              rows={2}
                              className="bg-white/50 dark:bg-slate-900/50"
                            />
                          </div>
                          {eventDetails.requirements.length > 1 && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => removeRequirement(index)}
                              className="text-destructive hover:text-destructive"
                            >
                              <X className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

              <Separator />

              <div className="flex justify-between items-center pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setActiveTab('person')}
                >
                  Back to Person Details
                </Button>

                <div className="flex items-center gap-4">
                  <Badge variant="outline" className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-green-400 rounded-full" />
                    {useManualDetails ? 'Manual Ready' : 'URL Ready'}
                  </Badge>
                  <Button
                    type="submit"
                    disabled={!isFormValid}
                    className="bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white px-8 py-2 flex items-center gap-2"
                  >
                    <Sparkles className="w-4 h-4" />
                    {useManualDetails ? 'Start Analysis' : 'Auto Extract & Analyze'}
                  </Button>
                </div>
              </div>
            </TabsContent>
          </form>
        </Tabs>
      </Card>
    </div>
  )
}