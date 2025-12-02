import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FileText, Upload, Download, Clock, Eye } from "lucide-react";
import { format } from "date-fns";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useState } from "react";
import { useToast } from "@/hooks/use-toast";

export default function Policies() {
  const { data: policies, refetch } = useQuery({ 
    queryKey: ["policies"], 
    queryFn: () => api.getPolicies() 
  });
  const { toast } = useToast();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUploading(true);
    // Simulate upload
    await api.uploadPolicy(new File([], "test"), "New Policy", "security", "IT");
    await refetch();
    setIsUploading(false);
    setUploadOpen(false);
    toast({ title: "Policy Uploaded", description: "The policy document has been indexed." });
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold tracking-tight">Policy Manager</h1>
          <p className="text-muted-foreground mt-2">Manage and upload company policies for the AI to reference.</p>
        </div>

        <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2 shadow-lg shadow-primary/20">
              <Upload className="w-4 h-4" />
              Upload Policy
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Upload Policy Document</DialogTitle>
              <DialogDescription>
                Upload a PDF document to be indexed by the compliance engine.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleUpload} className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Document Title</Label>
                <Input placeholder="e.g. Remote Work Policy 2024" required />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Policy Type</Label>
                  <Select required defaultValue="hr">
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="hr">HR</SelectItem>
                      <SelectItem value="security">Security</SelectItem>
                      <SelectItem value="legal">Legal</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Department</Label>
                  <Select required defaultValue="HR">
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="HR">HR</SelectItem>
                      <SelectItem value="IT">IT</SelectItem>
                      <SelectItem value="Legal">Legal</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label>File (PDF)</Label>
                <Input type="file" accept=".pdf" required />
              </div>
              <DialogFooter>
                <Button type="submit" disabled={isUploading}>
                  {isUploading ? "Uploading..." : "Upload Document"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {policies?.map((policy) => (
          <Card key={policy.id} className="group hover-elevate transition-all cursor-pointer">
            <CardHeader className="flex flex-row items-start justify-between pb-2 space-y-0">
              <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center group-hover:bg-primary/10 group-hover:text-primary transition-colors">
                <FileText className="w-5 h-5 text-muted-foreground group-hover:text-primary" />
              </div>
              <Badge variant="outline" className="font-mono">v{policy.version || "1.0"}</Badge>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <CardTitle className="text-base leading-tight mb-1 line-clamp-1">{policy.title}</CardTitle>
                <CardDescription className="flex items-center gap-2 text-xs">
                  {policy.department} • {format(new Date(policy.created_at), "MMM d, yyyy")}
                </CardDescription>
              </div>
              
              <div className="pt-2 flex items-center gap-2">
                <Badge variant="secondary" className="capitalize text-xs font-normal text-muted-foreground">
                  {policy.policy_type.replace("_", " ")}
                </Badge>
              </div>

              <div className="pt-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <Button variant="secondary" size="sm" className="w-full h-8 text-xs">
                  <Eye className="w-3 h-3 mr-2" />
                  View
                </Button>
                <Button variant="outline" size="sm" className="w-full h-8 text-xs">
                  <Download className="w-3 h-3 mr-2" />
                  Download
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
