export interface EventDetails {
  name: string
  type: string
  requirements: string[]
  audience: string
  format: string
}

export interface InformationSource {
  query: string
  source: string
  found_existing: boolean
}

export interface QualificationResult {
  person_name: string
  qualification_score: number
  qualification_reasoning: string
  searches_performed: number
  information_sources: InformationSource[]
  timestamp: string
  error?: string
}

export interface QualificationRequest {
  person_name: string
  event_details: EventDetails
}