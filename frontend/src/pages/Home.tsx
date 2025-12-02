import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { RiskBadge } from "@/components/RiskBadge";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis } from "recharts";
import { ShieldAlert, ShieldCheck, FileText, Activity } from "lucide-react";
import { format } from "date-fns";

export default function Home() {
  const { data: logs } = useQuery({ 
    queryKey: ["logs"], 
    queryFn: () => api.getLogs() 
  });
  
  const { data: policies } = useQuery({ 
    queryKey: ["policies"], 
    queryFn: () => api.getPolicies() 
  });

  const stats = {
    total: logs?.length || 0,
    highRisk: logs?.filter(l => l.overall_risk === "HIGH").length || 0,
    policies: policies?.length || 0,
    compliant: logs?.filter(l => l.overall_risk === "NONE").length || 0,
  };

  const riskData = [
    { name: "High", value: stats.highRisk, color: "hsl(var(--destructive))" },
    { name: "Medium", value: logs?.filter(l => l.overall_risk === "MEDIUM").length || 0, color: "hsl(var(--warning))" },
    { name: "Low", value: logs?.filter(l => l.overall_risk === "LOW").length || 0, color: "hsl(var(--primary))" },
    { name: "Compliant", value: stats.compliant, color: "hsl(var(--success))" },
  ].filter(d => d.value > 0);

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-display font-bold tracking-tight text-foreground">Dashboard</h1>
        <p className="text-muted-foreground mt-2">Overview of compliance status and recent activity.</p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="hover-elevate transition-all">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Checks</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
            <p className="text-xs text-muted-foreground">+20.1% from last month</p>
          </CardContent>
        </Card>
        <Card className="hover-elevate transition-all">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">High Risk Detected</CardTitle>
            <ShieldAlert className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">{stats.highRisk}</div>
            <p className="text-xs text-muted-foreground">Requires immediate attention</p>
          </CardContent>
        </Card>
        <Card className="hover-elevate transition-all">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Policies</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.policies}</div>
            <p className="text-xs text-muted-foreground">Up to date</p>
          </CardContent>
        </Card>
        <Card className="hover-elevate transition-all">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Compliance Rate</CardTitle>
            <ShieldCheck className="h-4 w-4 text-success" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-success">
              {stats.total ? Math.round((stats.compliant / stats.total) * 100) : 100}%
            </div>
            <p className="text-xs text-muted-foreground">Based on last 30 days</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="col-span-4 hover-elevate transition-all">
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Latest compliance checks performed.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-8">
              {logs?.slice(0, 5).map((log) => (
                <div key={log.id} className="flex items-center">
                  <div className="ml-4 space-y-1 flex-1">
                    <p className="text-sm font-medium leading-none truncate max-w-[300px]">{log.text}</p>
                    <p className="text-xs text-muted-foreground">
                      {log.department} • {format(new Date(log.created_at), "PP p")}
                    </p>
                  </div>
                  <RiskBadge risk={log.overall_risk} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
        <Card className="col-span-3 hover-elevate transition-all">
          <CardHeader>
            <CardTitle>Risk Distribution</CardTitle>
            <CardDescription>Breakdown of compliance risks.</CardDescription>
          </CardHeader>
          <CardContent className="pl-2">
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={riskData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {riskData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex justify-center gap-4 text-xs text-muted-foreground mt-4">
              {riskData.map((item) => (
                <div key={item.name} className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
                  {item.name}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
