import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Sparkles, Github } from 'lucide-react'

export function Header() {
  return (
    <header className="w-full">
      <div className="flex items-center justify-between py-6">
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-3">
            <div className="relative">
              <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div className="absolute -top-1 -right-1 w-4 h-4 bg-green-400 rounded-full animate-pulse" />
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-slate-900 to-slate-700 dark:from-white dark:to-gray-300 bg-clip-text text-transparent">
                AI Qualification Agent
              </h1>
              <p className="text-sm text-muted-foreground">Powered by advanced AI research</p>
            </div>
          </div>

          {/* Company Logos */}
          <div className="hidden md:flex items-center space-x-4 pl-6 border-l border-border">
            <div className="flex items-center space-x-2">
              <span className="text-xs text-muted-foreground font-medium">Powered by</span>
            </div>
            <div className="flex items-center space-x-4">
              <img
                src="https://proxyway.com/wp-content/uploads/2022/05/bright-data-logo.png?ver=1704718964"
                alt="Bright Data"
                className="h-6 w-auto opacity-80 hover:opacity-100 transition-opacity"
              />
              <span className="text-muted-foreground">×</span>
              <img
                src="https://cdn.prod.website-files.com/667da84c36c4c041ab413a2e/667db1fc27ea47ed322baf3b_1.png"
                alt="BELLE"
                className="h-6 w-auto opacity-80 hover:opacity-100 transition-opacity"
              />
            </div>
          </div>

          <Badge variant="secondary" className="hidden sm:flex items-center space-x-1">
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span>Live</span>
          </Badge>
        </div>

        <div className="flex items-center space-x-4">
          <Button
            variant="ghost"
            size="sm"
            className="text-muted-foreground hover:text-foreground"
            onClick={() => window.open('https://github.com', '_blank')}
          >
            <Github className="w-4 h-4 mr-2" />
            <span className="hidden sm:inline">Source</span>
          </Button>

          <div className="flex items-center space-x-1 text-sm text-muted-foreground">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span className="hidden sm:inline">System Operational</span>
          </div>
        </div>
      </div>

      <div className="h-px bg-gradient-to-r from-transparent via-border to-transparent" />
    </header>
  )
}