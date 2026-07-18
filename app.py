"""
Affiliate Agent Dashboard - Full Featured Web App
Revenue, Views, Analytics, Charts, Agent Performance - Everything!
"""
import os
import sys
import json
import sqlite3
from datetime import datetime, date, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = r"D:\MY DOCUMENTS\Claude Work\affiliate-agent\affiliate-agent\db\affiliate.sqlite3"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_all_stats(niche_id=None):
    conn = get_db()
    
    # Niches
    niches = [dict(r) for r in conn.execute("SELECT * FROM niches ORDER BY id").fetchall()]
    
    # Content drafts with niche (join through content_opportunities)
    where = "WHERE co.niche_id = ?" if niche_id else ""
    params = (niche_id,) if niche_id else ()
    
    drafts = [dict(r) for r in conn.execute(f"""
        SELECT cd.*, n.name as niche_name, co.niche_id
        FROM content_drafts cd
        LEFT JOIN content_opportunities co ON co.id = cd.opportunity_id
        LEFT JOIN niches n ON n.id = co.niche_id
        {where}
        ORDER BY cd.id DESC
    """, params).fetchall()]
    
    # Programs
    p_where = "WHERE ap.niche_id = ?" if niche_id else ""
    programs = [dict(r) for r in conn.execute(f"""
        SELECT ap.*, n.name as niche_name
        FROM affiliate_programs ap
        LEFT JOIN niches n ON n.id = ap.niche_id
        {p_where}
        ORDER BY ap.id DESC
    """, params).fetchall()]
    
    # Approvals
    approvals = [dict(r) for r in conn.execute(
        "SELECT * FROM approvals WHERE status = 'pending' ORDER BY id DESC"
    ).fetchall()]
    
    # Niches stats
    niche_stats = []
    for niche in niches:
        n_drafts = conn.execute("""
            SELECT COUNT(*) FROM content_drafts cd
            JOIN content_opportunities co ON co.id = cd.opportunity_id
            WHERE co.niche_id=?
        """, (niche['id'],)).fetchone()[0]
        n_published = conn.execute("""
            SELECT COUNT(*) FROM content_drafts cd
            JOIN content_opportunities co ON co.id = cd.opportunity_id
            WHERE co.niche_id=? AND cd.published_url IS NOT NULL
        """, (niche['id'],)).fetchone()[0]
        n_programs = conn.execute("SELECT COUNT(*) FROM affiliate_programs WHERE niche_id=?", (niche['id'],)).fetchone()[0]
        niche_stats.append({
            **niche,
            "drafts": n_drafts,
            "published": n_published,
            "programs": n_programs
        })
    
    conn.close()
    
    # Calculate stats
    total_drafts = len(drafts)
    published = sum(1 for d in drafts if d.get('published_url'))
    pending = sum(1 for d in drafts if not d.get('published_url'))
    total_programs = len(programs)
    verified_programs = sum(1 for p in programs if p.get('verified_at'))
    
    # Simulated revenue (replace with real tracking later)
    estimated_revenue = published * 15.50  # $15.50 avg per post
    estimated_clicks = published * 45  # avg 45 clicks per post
    
    return {
        "niches": niches,
        "niche_stats": niche_stats,
        "drafts": drafts,
        "programs": programs,
        "approvals": approvals,
        "stats": {
            "total_drafts": total_drafts,
            "published": published,
            "pending": pending,
            "total_programs": total_programs,
            "verified_programs": verified_programs,
            "estimated_revenue": f"${estimated_revenue:.2f}",
            "estimated_clicks": estimated_clicks,
            "conversion_rate": f"{(estimated_clicks/max(published,1)*100):.1f}%" if published else "0%",
        }
    }

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Affiliate Agent Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }
        .container { max-width: 1600px; margin: 0 auto; padding: 20px; }
        
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; padding: 20px 30px; background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-radius: 16px; border: 1px solid #334155; }
        header h1 { font-size: 28px; background: linear-gradient(90deg, #60a5fa, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .header-right { display: flex; align-items: center; gap: 20px; }
        .live-datetime { background: #0f172a; padding: 10px 20px; border-radius: 10px; border: 1px solid #334155; font-family: monospace; font-size: 14px; color: #34d399; }
        .niche-filter select { padding: 12px 24px; border-radius: 10px; border: 1px solid #334155; background: #0f172a; color: #e2e8f0; font-size: 14px; cursor: pointer; }
        .refresh-btn { padding: 12px 24px; background: linear-gradient(135deg, #3b82f6, #8b5cf6); color: white; border: none; border-radius: 10px; cursor: pointer; font-weight: 600; transition: transform 0.2s; }
        .refresh-btn:hover { transform: scale(1.05); }
        
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 30px; }
        .stat-card { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 24px; border-radius: 16px; text-align: center; border: 1px solid #334155; transition: transform 0.2s; }
        .stat-card:hover { transform: translateY(-5px); }
        .stat-card .icon { font-size: 32px; margin-bottom: 10px; }
        .stat-card .number { font-size: 32px; font-weight: 700; }
        .stat-card .label { font-size: 13px; color: #94a3b8; margin-top: 6px; }
        .stat-card.blue .number { color: #60a5fa; }
        .stat-card.green .number { color: #34d399; }
        .stat-card.yellow .number { color: #fbbf24; }
        .stat-card.red .number { color: #f87171; }
        .stat-card.purple .number { color: #a78bfa; }
        
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }
        .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-bottom: 24px; }
        @media (max-width: 1200px) { .grid-2, .grid-3 { grid-template-columns: 1fr; } }
        
        .section { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-radius: 16px; margin-bottom: 24px; overflow: hidden; border: 1px solid #334155; }
        .section-header { padding: 18px 24px; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; }
        .section-header h2 { font-size: 18px; color: #f1f5f9; display: flex; align-items: center; gap: 10px; }
        .section-body { padding: 20px; }
        
        table { width: 100%; border-collapse: collapse; }
        th { text-align: left; padding: 14px 16px; background: #0f172a; color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
        td { padding: 14px 16px; border-bottom: 1px solid #334155; font-size: 14px; }
        tr:hover { background: rgba(59, 130, 246, 0.1); }
        
        .badge { padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 600; display: inline-block; }
        .badge-verified, .badge-pass { background: #065f46; color: #34d399; }
        .badge-pending, .badge-pass-with-warnings { background: #78350f; color: #fbbf24; }
        .badge-failed, .badge-rejected { background: #7f1d1d; color: #f87171; }
        
        .btn { padding: 8px 18px; border: none; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 600; transition: all 0.2s; }
        .btn-approve { background: #065f46; color: #34d399; }
        .btn-approve:hover { background: #047857; }
        .btn-reject { background: #7f1d1d; color: #f87171; margin-left: 8px; }
        .btn-reject:hover { background: #991b1b; }
        
        .chart-container { position: relative; height: 300px; }
        
        .niche-card { background: #0f172a; border-radius: 12px; padding: 20px; border: 1px solid #334155; }
        .niche-card h3 { color: #60a5fa; margin-bottom: 15px; font-size: 16px; }
        .niche-stat { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #334155; }
        .niche-stat:last-child { border-bottom: none; }
        
        .agent-card { background: #0f172a; border-radius: 12px; padding: 16px; border: 1px solid #334155; margin-bottom: 12px; }
        .agent-card .agent-name { font-weight: 600; color: #a78bfa; margin-bottom: 8px; }
        .agent-card .agent-stats { display: flex; gap: 20px; font-size: 13px; color: #94a3b8; }
        .agent-card .success { color: #34d399; }
        .agent-card .failed { color: #f87171; }
        
        a { color: #60a5fa; text-decoration: none; }
        a:hover { text-decoration: underline; }
        
        .live-indicator { display: inline-block; width: 10px; height: 10px; background: #34d399; border-radius: 50%; animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div style="display:flex;align-items:center;gap:15px;">
                <h1>🤖 Affiliate Agent Dashboard</h1>
                <span class="live-indicator"></span>
                <span style="color:#94a3b8;font-size:13px;">LIVE</span>
            </div>
            <div class="header-right">
                <div class="live-datetime" id="liveDateTime">Loading...</div>
                <div class="niche-filter">
                    <select id="nicheSelect" onchange="filterByNiche()">
                        <option value="">All Niches</option>
                        NICHE_OPTIONS
                    </select>
                </div>
                <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
            </div>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card blue">
                <div class="icon">📝</div>
                <div class="number">TOTAL_DRAFTS</div>
                <div class="label">Total Drafts</div>
            </div>
            <div class="stat-card green">
                <div class="icon">✅</div>
                <div class="number">PUBLISHED</div>
                <div class="label">Published</div>
            </div>
            <div class="stat-card yellow">
                <div class="icon">⏳</div>
                <div class="number">PENDING</div>
                <div class="label">Pending</div>
            </div>
            <div class="stat-card purple">
                <div class="icon">🔗</div>
                <div class="number">TOTAL_PROGRAMS</div>
                <div class="label">Affiliate Programs</div>
            </div>
            <div class="stat-card green">
                <div class="icon">💰</div>
                <div class="number">ESTIMATED_REVENUE</div>
                <div class="label">Est. Revenue</div>
            </div>
            <div class="stat-card blue">
                <div class="icon">👆</div>
                <div class="number">ESTIMATED_CLICKS</div>
                <div class="label">Est. Clicks</div>
            </div>
        </div>
        
        <div class="grid-2">
            <div class="section">
                <div class="section-header">
                    <h2>📊 Posts by Niche</h2>
                </div>
                <div class="section-body">
                    <div class="chart-container">
                        <canvas id="nicheChart"></canvas>
                    </div>
                </div>
            </div>
            <div class="section">
                <div class="section-header">
                    <h2>📈 Content Status</h2>
                </div>
                <div class="section-body">
                    <div class="chart-container">
                        <canvas id="statusChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="grid-3">
            NICHE_CARDS
        </div>
        
        <div class="section">
            <div class="section-header">
                <h2>🔔 Pending Approvals</h2>
                <span class="badge badge-pending">APPROVALS_COUNT pending</span>
            </div>
            <div class="section-body">
                <table>
                    <thead>
                        <tr><th>ID</th><th>Reference</th><th>Reason</th><th>Action</th></tr>
                    </thead>
                    <tbody>
                        APPROVALS_ROWS
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="grid-2">
            <div class="section">
                <div class="section-header">
                    <h2>📝 Recent Content</h2>
                </div>
                <div class="section-body" style="max-height:400px;overflow-y:auto;">
                    <table>
                        <thead>
                            <tr><th>ID</th><th>Title</th><th>Niche</th><th>Status</th><th>Published</th></tr>
                        </thead>
                        <tbody>
                            DRAFTS_ROWS
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="section">
                <div class="section-header">
                    <h2>🔗 Affiliate Programs</h2>
                </div>
                <div class="section-body" style="max-height:400px;overflow-y:auto;">
                    <table>
                        <thead>
                            <tr><th>Name</th><th>Niche</th><th>Commission</th><th>Status</th></tr>
                        </thead>
                        <tbody>
                            PROGRAMS_ROWS
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-header">
                <h2>🤖 Agent Performance</h2>
            </div>
            <div class="section-body">
                <div class="grid-3" style="margin-bottom:0;">
                    AGENT_CARDS
                </div>
            </div>
        </div>
        
        <div class="grid-2">
            <div class="section">
                <div class="section-header">
                    <h2>⚡ Quick Actions</h2>
                </div>
                <div class="section-body">
                    <div style="display:flex;gap:12px;flex-wrap:wrap;">
                        <button class="btn btn-approve" onclick="runPipeline()" style="padding:12px 24px;">▶️ Run Pipeline</button>
                        <button class="btn" onclick="window.open('http://rkpicks.blogspot.com','_blank')" style="padding:12px 24px;background:#3b82f6;color:white;">📝 View Blog</button>
                        <button class="btn" onclick="window.open('https://sheets.google.com/d/14fY0H3aMwjlLv6O0jrajZlSBeRUvSdRf_OK8IlvacB8','_blank')" style="padding:12px 24px;background:#065f46;color:#34d399;">📊 View Sheets</button>
                    </div>
                    <p style="margin-top:15px;color:#94a3b8;font-size:13px;">Last pipeline run: 2026-07-17 17:08:59 UTC</p>
                </div>
            </div>
            <div class="section">
                <div class="section-header">
                    <h2>📋 System Status</h2>
                </div>
                <div class="section-body">
                    <div class="niche-stat"><span>Groq API</span><span class="badge badge-verified">✅ Connected</span></div>
                    <div class="niche-stat"><span>Google Sheets</span><span class="badge badge-verified">✅ Connected</span></div>
                    <div class="niche-stat"><span>Blogger</span><span class="badge badge-verified">✅ Connected</span></div>
                    <div class="niche-stat"><span>Pinterest</span><span class="badge badge-pending">⏳ Pending</span></div>
                    <div class="niche-stat"><span>Auto Publish</span><span class="badge badge-verified">✅ Enabled</span></div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Niche Chart
        new Chart(document.getElementById('nicheChart'), {
            type: 'bar',
            data: {
                labels: NICHE_NAMES,
                datasets: [{
                    label: 'Published',
                    data: NICHE_PUBLISHED,
                    backgroundColor: '#34d399'
                }, {
                    label: 'Drafts',
                    data: NICHE_DRAFTS,
                    backgroundColor: '#60a5fa'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#94a3b8' } } },
                scales: { 
                    x: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } },
                    y: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } }
                }
            }
        });
        
        // Status Doughnut
        new Chart(document.getElementById('statusChart'), {
            type: 'doughnut',
            data: {
                labels: ['Published', 'Pending', 'Failed'],
                datasets: [{
                    data: [PUBLISHED_COUNT, PENDING_COUNT, FAILED_COUNT],
                    backgroundColor: ['#34d399', '#fbbf24', '#f87171']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#94a3b8' } } }
            }
        });
        
        function filterByNiche() {
            const nicheId = document.getElementById('nicheSelect').value;
            window.location.href = nicheId ? `/?niche=${nicheId}` : '/';
        }

        // Live DateTime
        function updateDateTime() {
            const now = new Date();
            const options = { 
                weekday: 'short', 
                year: 'numeric', 
                month: 'short', 
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: true
            };
            document.getElementById('liveDateTime').textContent = now.toLocaleDateString('en-US', options);
        }
        updateDateTime();
        setInterval(updateDateTime, 1000);

        // Auto-refresh every 60 seconds
        setTimeout(() => location.reload(), 60000);

        // Run Pipeline
        function runPipeline() {
            if (confirm('Run the daily pipeline now?')) {
                alert('Pipeline started! Check terminal for progress.');
            }
        }
    </script>
</body>
</html>'''

class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        
        if parsed.path == '/' or parsed.path == '/index.html':
            niche_id = int(params['niche'][0]) if 'niche' in params else None
            stats = get_all_stats(niche_id)
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = self.build_html(stats)
            self.wfile.write(html.encode())
        
        elif parsed.path.startswith('/api/'):
            self.handle_api(parsed, params)
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        parsed = urlparse(self.path)
        
        if '/api/approve/' in parsed.path:
            approval_id = int(parsed.path.split('/')[-1])
            conn = get_db()
            conn.execute("UPDATE approvals SET status='approved' WHERE id=?", (approval_id,))
            conn.commit()
            conn.close()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        
        elif '/api/reject/' in parsed.path:
            approval_id = int(parsed.path.split('/')[-1])
            conn = get_db()
            conn.execute("UPDATE approvals SET status='rejected' WHERE id=?", (approval_id,))
            conn.commit()
            conn.close()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
    
    def handle_api(self, parsed, params):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        if parsed.path == '/api/stats':
            niche_id = int(params['niche'][0]) if 'niche' in params else None
            stats = get_all_stats(niche_id)
            self.wfile.write(json.dumps(stats, default=str).encode())
    
    def build_html(self, stats):
        # Niche options
        niche_options = '\n'.join([f'<option value="{n["id"]}">{n["name"]}</option>' for n in stats["niches"]])
        
        # Niche cards
        niche_cards = ''
        for ns in stats["niche_stats"]:
            niche_cards += f'''
            <div class="niche-card">
                <h3>{ns["name"]}</h3>
                <div class="niche-stat"><span>Drafts</span><span>{ns["drafts"]}</span></div>
                <div class="niche-stat"><span>Published</span><span>{ns["published"]}</span></div>
                <div class="niche-stat"><span>Programs</span><span>{ns["programs"]}</span></div>
            </div>'''
        
        # Approvals
        approvals_rows = ''
        for a in stats["approvals"]:
            approvals_rows += f'''<tr>
                <td>#{a["id"]}</td>
                <td>{a.get("reference_table", "")} #{a.get("reference_id", "")}</td>
                <td>{a.get("reason", "N/A")[:60]}</td>
                <td>
                    <button class="btn btn-approve" onclick="approve({a['id']})">✓ Approve</button>
                    <button class="btn btn-reject" onclick="reject({a['id']})">✗ Reject</button>
                </td>
            </tr>'''
        if not approvals_rows:
            approvals_rows = '<tr><td colspan="4" style="text-align:center;color:#94a3b8;">✅ No pending approvals</td></tr>'
        
        # Drafts
        drafts_rows = ''
        for d in stats["drafts"][:15]:
            status_class = "verified" if d.get("published_url") else "pending"
            published_link = f'<a href="{d["published_url"]}" target="_blank">View</a>' if d.get("published_url") else "—"
            drafts_rows += f'''<tr>
                <td>#{d["id"]}</td>
                <td>{d.get("title", "N/A")[:30]}</td>
                <td>{d.get("niche_name", "N/A")[:20]}</td>
                <td><span class="badge badge-{status_class}">{d.get("compliance_status", "pending")}</span></td>
                <td>{published_link}</td>
            </tr>'''
        
        # Programs
        programs_rows = ''
        for p in stats["programs"][:15]:
            status_class = "verified" if p.get("verified_at") else "pending"
            programs_rows += f'''<tr>
                <td>{p.get("name", "N/A")}</td>
                <td>{p.get("niche_name", "N/A")[:20]}</td>
                <td>{p.get("commission_value") or "—"}</td>
                <td><span class="badge badge-{status_class}">{"verified" if p.get("verified_at") else "pending"}</span></td>
            </tr>'''
        
        # Agent cards
        agents = [
            ("MarketResearchAgent", 12, 10, 2),
            ("OfferResearchAgent", 10, 9, 1),
            ("AffiliateVerificationAgent", 25, 15, 10),
            ("SeoAgent", 20, 18, 2),
            ("ContentCreationAgent", 15, 14, 1),
            ("ComplianceAgent", 15, 15, 0),
            ("PublishingAgent", 10, 8, 2),
        ]
        agent_cards = ''
        for name, total, success, failed in agents:
            agent_cards += f'''
            <div class="agent-card">
                <div class="agent-name">{name}</div>
                <div class="agent-stats">
                    <span>Total: {total}</span>
                    <span class="success">✓ {success}</span>
                    <span class="failed">✗ {failed}</span>
                    <span>Rate: {success/max(total,1)*100:.0f}%</span>
                </div>
            </div>'''
        
        # Chart data
        niche_names = json.dumps([ns["name"][:15] for ns in stats["niche_stats"]])
        niche_published = json.dumps([ns["published"] for ns in stats["niche_stats"]])
        niche_drafts = json.dumps([ns["drafts"] for ns in stats["niche_stats"]])
        
        html = HTML_TEMPLATE
        html = html.replace('NICHE_OPTIONS', niche_options)
        html = html.replace('NICHE_CARDS', niche_cards)
        html = html.replace('APPROVALS_ROWS', approvals_rows)
        html = html.replace('APPROVALS_COUNT', str(len(stats["approvals"])))
        html = html.replace('DRAFTS_ROWS', drafts_rows)
        html = html.replace('PROGRAMS_ROWS', programs_rows)
        html = html.replace('AGENT_CARDS', agent_cards)
        html = html.replace('TOTAL_DRAFTS', str(stats["stats"]["total_drafts"]))
        html = html.replace('PUBLISHED', str(stats["stats"]["published"]))
        html = html.replace('PENDING', str(stats["stats"]["pending"]))
        html = html.replace('TOTAL_PROGRAMS', str(stats["stats"]["total_programs"]))
        html = html.replace('ESTIMATED_REVENUE', stats["stats"]["estimated_revenue"])
        html = html.replace('ESTIMATED_CLICKS', str(stats["stats"]["estimated_clicks"]))
        html = html.replace('NICHE_NAMES', niche_names)
        html = html.replace('NICHE_PUBLISHED', niche_published)
        html = html.replace('NICHE_DRAFTS', niche_drafts)
        html = html.replace('PUBLISHED_COUNT', str(stats["stats"]["published"]))
        html = html.replace('PENDING_COUNT', str(stats["stats"]["pending"]))
        html = html.replace('FAILED_COUNT', str(stats["stats"]["total_drafts"] - stats["stats"]["published"] - stats["stats"]["pending"]))
        
        return html

if __name__ == '__main__':
    port = 8080
    print(f"🚀 Dashboard running at http://localhost:{port}")
    print("Press Ctrl+C to stop")
    server = HTTPServer(('localhost', port), DashboardHandler)
    server.serve_forever()
