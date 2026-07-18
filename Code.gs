/**
 * Affiliate Marketing Dashboard - Google Apps Script
 * Web app for tracking traffic, income, and posts
 */

// Sheet names
const SHEET_NICHES = 'Niches';
const SHEET_OFFERS = 'Offers';
const SHEET_POSTS = 'Posts';
const SHEET_ANALYTICS = 'Analytics';
const SHEET_INCOME = 'Income';
const SHEET_AGENTS = 'Agents';

/**
 * Serve the dashboard HTML
 */
function doGet(e) {
  return HtmlService.createHtmlOutputFromFile('index')
    .setTitle('Affiliate Marketing Dashboard')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

/**
 * Get dashboard summary data
 */
function getDashboardSummary() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  
  const niches = getSheetData(ss, SHEET_NICHES);
  const posts = getSheetData(ss, SHEET_POSTS);
  const income = getSheetData(ss, SHEET_INCOME);
  const agents = getSheetData(ss, SHEET_AGENTS);
  
  const totalRevenue = income.reduce((sum, row) => sum + (parseFloat(row.Amount) || 0), 0);
  const activeNiches = niches.filter(n => n.Status === 'active').length;
  const activeAgents = agents.filter(a => a.Status === 'running').length;
  
  return {
    totalNiches: niches.length,
    activeNiches: activeNiches,
    totalPosts: posts.length,
    totalRevenue: totalRevenue.toFixed(2),
    activeAgents: activeAgents,
    niches: niches,
    recentPosts: posts.slice(-10).reverse(),
    recentIncome: income.slice(-10).reverse()
  };
}

/**
 * Get niche performance data
 */
function getNichePerformance() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const niches = getSheetData(ss, SHEET_NICHES);
  const analytics = getSheetData(ss, SHEET_ANALYTICS);
  
  return niches.map(niche => {
    const nicheAnalytics = analytics.filter(a => a.Niche === niche.Name);
    const totalClicks = nicheAnalytics.reduce((sum, a) => sum + (parseInt(a.Clicks) || 0), 0);
    const totalImpressions = nicheAnalytics.reduce((sum, a) => sum + (parseInt(a.Impressions) || 0), 0);
    const totalRevenue = nicheAnalytics.reduce((sum, a) => sum + (parseFloat(a.Revenue) || 0), 0);
    
    return {
      name: niche.Name,
      status: niche.Status,
      posts: parseInt(niche['Total Posts']) || 0,
      clicks: totalClicks,
      impressions: totalImpressions,
      revenue: totalRevenue.toFixed(2)
    };
  });
}

/**
 * Get daily analytics for charts
 */
function getDailyAnalytics(days = 30) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const analytics = getSheetData(ss, SHEET_ANALYTICS);
  
  const today = new Date();
  const startDate = new Date(today);
  startDate.setDate(startDate.getDate() - days);
  
  const dailyData = {};
  
  analytics.forEach(row => {
    const date = row.Date;
    if (date && new Date(date) >= startDate) {
      if (!dailyData[date]) {
        dailyData[date] = { clicks: 0, impressions: 0, revenue: 0 };
      }
      dailyData[date].clicks += parseInt(row.Clicks) || 0;
      dailyData[date].impressions += parseInt(row.Impressions) || 0;
      dailyData[date].revenue += parseFloat(row.Revenue) || 0;
    }
  });
  
  return Object.entries(dailyData)
    .sort(([a], [b]) => new Date(a) - new Date(b))
    .map(([date, data]) => ({
      date,
      ...data,
      revenue: data.revenue.toFixed(2)
    }));
}

/**
 * Get top performing posts
 */
function getTopPosts(limit = 10) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const posts = getSheetData(ss, SHEET_POSTS);
  const analytics = getSheetData(ss, SHEET_ANALYTICS);
  
  return posts
    .map(post => {
      const postAnalytics = analytics.filter(a => a['Post ID'] === post.ID);
      const totalClicks = postAnalytics.reduce((sum, a) => sum + (parseInt(a.Clicks) || 0), 0);
      const totalSaves = postAnalytics.reduce((sum, a) => sum + (parseInt(a.Saves) || 0), 0);
      
      return {
        ...post,
        totalClicks,
        totalSaves
      };
    })
    .sort((a, b) => b.totalClicks - a.totalClicks)
    .slice(0, limit);
}

/**
 * Get income breakdown by niche
 */
function getIncomeByNiche() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const income = getSheetData(ss, SHEET_INCOME);
  
  const byNiche = {};
  
  income.forEach(row => {
    const niche = row.Niche || 'Unknown';
    if (!byNiche[niche]) {
      byNiche[niche] = { total: 0, count: 0 };
    }
    byNiche[niche].total += parseFloat(row.Amount) || 0;
    byNiche[niche].count++;
  });
  
  return Object.entries(byNiche)
    .map(([niche, data]) => ({
      niche,
      total: data.total.toFixed(2),
      count: data.count
    }))
    .sort((a, b) => b.total - a.total);
}

/**
 * Get agent status
 */
function getAgentStatus() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const agents = getSheetData(ss, SHEET_AGENTS);
  
  return agents.map(agent => ({
    name: agent['Agent Name'],
    niche: agent.Niche,
    status: agent.Status,
    lastRun: agent['Last Run'],
    pinsCreated: parseInt(agent['Pins Created']) || 0,
    errors: parseInt(agent.Errors) || 0
  }));
}

/**
 * Helper function to get sheet data as array of objects
 */
function getSheetData(spreadsheet, sheetName) {
  try {
    const sheet = spreadsheet.getSheetByName(sheetName);
    if (!sheet) return [];
    
    const data = sheet.getDataRange().getValues();
    if (data.length < 2) return [];
    
    const headers = data[0];
    return data.slice(1).map(row => {
      const obj = {};
      headers.forEach((header, i) => {
        obj[header] = row[i];
      });
      return obj;
    });
  } catch (e) {
    console.error(`Error reading ${sheetName}:`, e);
    return [];
  }
}

/**
 * Add a new niche manually
 */
function addNiche(name) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(SHEET_NICHES);
  
  sheet.appendRow([
    sheet.getLastRow(),
    name,
    'active',
    0,
    'US',
    0,
    0,
    0,
    new Date().toISOString(),
    new Date().toISOString()
  ]);
  
  return { success: true, message: `Niche "${name}" added` };
}

/**
 * Update niche status
 */
function updateNicheStatus(nicheName, status) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(SHEET_NICHES);
  const data = sheet.getDataRange().getValues();
  
  for (let i = 1; i < data.length; i++) {
    if (data[i][1] === nicheName) {
      sheet.getRange(i + 1, 3).setValue(status);
      return { success: true };
    }
  }
  
  return { success: false, message: 'Niche not found' };
}

/**
 * Get hourly posting schedule
 */
function getPostingSchedule() {
  return {
    optimalHours: [8, 9, 12, 13, 14, 19, 20, 21],
    maxPinsPerDay: 15,
    minIntervalMinutes: 10
  };
}
