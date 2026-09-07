import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity, Database, Server, Clock } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

export function DashboardPage() {
    const [stats, setStats] = useState<any>(null);
    const [logs, setLogs] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchData = async () => {
        try {
            const statsRes = await fetch("/api/v1/monitor/stats");
            const logsRes = await fetch("/api/v1/monitor/logs");

            if (statsRes.ok) setStats(await statsRes.json());
            if (logsRes.ok) setLogs(await logsRes.json());
        } catch (error) {
            console.error("Failed to fetch dashboard data", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 30000); // Live update every 30s
        return () => clearInterval(interval);
    }, []);

    if (loading) {
        return <div className="flex items-center justify-center h-screen">Loading Metrics...</div>;
    }

    return (
        <div className="container mx-auto p-8 space-y-8">
            <h1 className="text-3xl font-bold tracking-tight">System Dashboard</h1>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Queries (Today)</CardTitle>
                        <Activity className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats?.total_queries || 0}</div>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Cache Hit Rate</CardTitle>
                        <Database className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats?.cache_hit_rate || 0}%</div>
                        <p className="text-xs text-muted-foreground">Local + Semantic Cache</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Avg Latency</CardTitle>
                        <Clock className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats?.avg_latency || 0} ms</div>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">System Status</CardTitle>
                        <Server className="h-4 w-4 text-green-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-green-500">Operational</div>
                    </CardContent>
                </Card>
            </div>

            <div className="space-y-4">
                <h2 className="text-xl font-semibold">Recent Query Logs</h2>
                <div className="rounded-md border">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Time</TableHead>
                                <TableHead>Query</TableHead>
                                <TableHead>Source</TableHead>
                                <TableHead className="text-right">Latency</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {logs.map((log, i) => (
                                <TableRow key={i}>
                                    <TableCell className="font-mono text-xs text-muted-foreground">
                                        {new Date(log.Time).toLocaleTimeString()}
                                    </TableCell>
                                    <TableCell className="font-medium max-w-md truncate" title={log.Query}>
                                        {log.Query}
                                    </TableCell>
                                    <TableCell>
                                        <span className={cn(
                                            "inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ring-1 ring-inset",
                                            // "Error" used to fall into the catch-all branch below and render as a
                                            // green "healthy" badge, hiding failed queries from this table.
                                            log.Source.includes("Error") ? "bg-red-50 text-red-700 ring-red-700/10" :
                                                log.Source.includes("RAG") ? "bg-blue-50 text-blue-700 ring-blue-700/10" :
                                                    log.Source.includes("Web") ? "bg-purple-50 text-purple-700 ring-purple-700/10" :
                                                        log.Source.includes("Cache") ? "bg-green-50 text-green-700 ring-green-600/20" :
                                                            "bg-gray-50 text-gray-700 ring-gray-600/20"
                                        )}>
                                            {log.Source}
                                        </span>
                                    </TableCell>
                                    <TableCell className="text-right text-xs">
                                        {log["Latency (ms)"]} ms
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </div>
            </div>
        </div>
    );
}
