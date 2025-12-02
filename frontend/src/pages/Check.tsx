import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, ComplianceCheckResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { RiskBadge } from "@/components/RiskBadge";
import { Loader2, ArrowRight, CheckCircle2, AlertTriangle, Copy } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function Check() {
  const [text, setText] = useState("");
  const [department, setDepartment] = useState("Sales");
  const [type, setType] = useState("external_communication");
  const { toast } = useToast();

  const mutation = useMutation({
    mutationFn: () => api.checkCompliance(text, department, type),
    onSuccess: (data) => {
      toast({
        title: "Check Complete",
        description: `Risk Level: ${data.overall_risk}`,
        variant: data.overall_risk === "HIGH" ? "destructive" : "default",
      });
    },
  });

  const handleCheck = () => {
    if (!text.trim()) return;
    mutation.mutate();
  };

  const handleCopy = (content: string) => {
    navigator.clipboard.writeText(content);
    toast({ title: "Copied to clipboard" });
  };

  return (
    <div className="grid lg:grid-cols-2 gap-6 h-[calc(100vh-8rem)] animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Left Column: Input */}
      <div className="flex flex-col gap-4 h-full">
        <div>
          <h1 className="text-3xl font-display font-bold tracking-tight mb-2">Compliance Check</h1>
          <p className="text-muted-foreground">Draft your content and check against company policies in real-time.</p>
        </div>

        <Card className="flex-1 flex flex-col hover-elevate border-sidebar-border/20">
          <CardHeader className="pb-4">
            <div className="flex gap-4">
              <div className="flex-1 space-y-2">
                <Label>Department</Label>
                <Select value={department} onValueChange={setDepartment}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Sales">Sales</SelectItem>
                    <SelectItem value="Marketing">Marketing</SelectItem>
                    <SelectItem value="HR">HR</SelectItem>
                    <SelectItem value="IT">IT</SelectItem>
                    <SelectItem value="Legal">Legal</SelectItem>
                    <SelectItem value="Support">Support</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex-1 space-y-2">
                <Label>Policy Type</Label>
                <Select value={type} onValueChange={setType}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="confidentiality">Confidentiality</SelectItem>
                    <SelectItem value="external_communication">External Comm</SelectItem>
                    <SelectItem value="data_privacy">Data Privacy</SelectItem>
                    <SelectItem value="security">Security</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col min-h-0">
            <Textarea
              placeholder="Type or paste your content here..."
              className="flex-1 resize-none font-mono text-sm leading-relaxed p-4 focus-visible:ring-primary/20"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
            <div className="pt-4 flex justify-end">
              <Button 
                size="lg" 
                onClick={handleCheck} 
                disabled={mutation.isPending || !text.trim()}
                className="w-full md:w-auto transition-all shadow-lg shadow-primary/20"
              >
                {mutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    Run Compliance Check
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Right Column: Results */}
      <div className="flex flex-col gap-4 h-full lg:pt-[88px]">
        {mutation.data ? (
          <div className="flex flex-col gap-4 h-full animate-in fade-in slide-in-from-right-4 duration-500">
            {/* Summary Card */}
            <Card className="border-l-4 border-l-transparent data-[risk=HIGH]:border-l-destructive data-[risk=MEDIUM]:border-l-warning data-[risk=LOW]:border-l-primary data-[risk=NONE]:border-l-success hover-elevate"
                  data-risk={mutation.data.overall_risk}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle>Analysis Result</CardTitle>
                  <RiskBadge risk={mutation.data.overall_risk} />
                </div>
                <CardDescription>
                  {mutation.data.issues.length} issue(s) found in your text.
                </CardDescription>
              </CardHeader>
            </Card>

            <Tabs defaultValue="issues" className="flex-1 flex flex-col min-h-0">
              <TabsList className="w-full justify-start border-b rounded-none bg-transparent p-0 h-auto">
                <TabsTrigger 
                  value="issues" 
                  className="data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none px-4 py-3"
                >
                  Issues Detected
                </TabsTrigger>
                <TabsTrigger 
                  value="rewrite" 
                  className="data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none px-4 py-3"
                  disabled={!mutation.data.suggested_text}
                >
                  Suggested Rewrite
                </TabsTrigger>
              </TabsList>

              <div className="flex-1 bg-card border rounded-b-lg mt-[-1px] overflow-hidden shadow-sm">
                <TabsContent value="issues" className="h-full m-0 overflow-auto p-6 space-y-4">
                  {mutation.data.issues.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-muted-foreground space-y-4">
                      <div className="h-16 w-16 rounded-full bg-success/10 flex items-center justify-center">
                        <CheckCircle2 className="h-8 w-8 text-success" />
                      </div>
                      <p className="text-lg font-medium text-foreground">No Issues Found</p>
                      <p className="text-sm max-w-xs text-center">Your text appears to be compliant with the selected policies.</p>
                    </div>
                  ) : (
                    mutation.data.issues.map((issue, idx) => (
                      <div key={idx} className="p-4 rounded-lg border bg-muted/30 space-y-2 animate-in fade-in slide-in-from-bottom-2" style={{ animationDelay: `${idx * 100}ms` }}>
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <AlertTriangle className="h-4 w-4 text-warning shrink-0" />
                            <span className="font-semibold text-sm text-foreground">{issue.type}</span>
                          </div>
                          {issue.policy_reference && (
                            <span className="text-xs font-mono text-muted-foreground bg-muted px-2 py-1 rounded">
                              {issue.policy_reference}
                            </span>
                          )}
                        </div>
                        
                        {issue.excerpt && (
                          <div className="text-sm bg-destructive/5 text-destructive p-2 rounded border border-destructive/10 font-mono">
                            "{issue.excerpt}"
                          </div>
                        )}
                        
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          {issue.explanation}
                        </p>
                      </div>
                    ))
                  )}
                </TabsContent>

                <TabsContent value="rewrite" className="h-full m-0 p-0 relative group">
                  <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button size="sm" variant="outline" onClick={() => handleCopy(mutation.data.suggested_text || "")}>
                      <Copy className="h-3 w-3 mr-2" />
                      Copy
                    </Button>
                  </div>
                  <Textarea 
                    readOnly 
                    className="h-full border-0 resize-none p-6 font-mono text-sm leading-relaxed focus-visible:ring-0 bg-success/5 text-foreground"
                    value={mutation.data.suggested_text || ""}
                  />
                </TabsContent>
              </div>
            </Tabs>
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-muted-foreground border-2 border-dashed rounded-xl bg-muted/10">
            <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center mb-4">
              <ArrowRight className="h-6 w-6 text-muted-foreground/50" />
            </div>
            <p className="font-medium">Ready to Analyze</p>
            <p className="text-sm">Enter text and click check to see results.</p>
          </div>
        )}
      </div>
    </div>
  );
}
