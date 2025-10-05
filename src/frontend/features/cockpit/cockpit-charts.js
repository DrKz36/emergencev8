/**
 * Cockpit Charts Module
 * Interactive data visualizations (Timeline, Pie, Line charts)
 */

import { api } from '../../shared/api-client.js';

export class CockpitCharts {
    constructor() {
        this.container = null;
        this.charts = {
            timeline: null,
            distribution: null,
            usage: null
        };
        this.chartData = {};
    }

    /**
     * Initialize charts module
     */
    async init(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('Cockpit charts container not found:', containerId);
            return;
        }

        console.log('🎨 Initializing Cockpit Charts...');
        this.render();

        // Wait for DOM to be fully ready
        await new Promise(resolve => setTimeout(resolve, 100));

        console.log('📊 Loading chart data...');
        await this.loadChartData();
        console.log('🖼️ Rendering charts...');
        this.renderCharts();
        console.log('✅ Cockpit Charts initialized');
    }

    /**
     * Render charts UI structure
     */
    render() {
        this.container.innerHTML = `
            <div class="cockpit-charts">
                <div class="charts-header">
                    <h2>📈 Graphiques Interactifs</h2>
                    <div class="charts-controls">
                        <select class="period-selector">
                            <option value="7d">7 derniers jours</option>
                            <option value="30d" selected>30 derniers jours</option>
                            <option value="90d">90 derniers jours</option>
                            <option value="1y">1 an</option>
                        </select>
                        <button class="btn-refresh" title="Actualiser">🔄</button>
                    </div>
                </div>

                <div class="charts-grid">
                    <!-- Timeline Chart -->
                    <div class="chart-container timeline-chart">
                        <div class="chart-header">
                            <h3>📊 Timeline d'Activité</h3>
                            <div class="chart-legend">
                                <span class="legend-item">
                                    <span class="legend-dot messages"></span>
                                    Messages
                                </span>
                                <span class="legend-item">
                                    <span class="legend-dot threads"></span>
                                    Threads
                                </span>
                            </div>
                        </div>
                        <div class="chart-canvas-wrapper">
                            <canvas id="timeline-chart"></canvas>
                        </div>
                    </div>

                    <!-- Distribution Pie Chart -->
                    <div class="chart-container distribution-chart">
                        <div class="chart-header">
                            <h3>🥧 Distribution des Agents</h3>
                            <select class="chart-filter">
                                <option value="messages">Par Messages</option>
                                <option value="threads">Par Threads</option>
                                <option value="tokens">Par Tokens</option>
                            </select>
                        </div>
                        <div class="chart-canvas-wrapper">
                            <canvas id="distribution-chart"></canvas>
                        </div>
                        <div class="chart-stats" id="distribution-stats"></div>
                    </div>

                    <!-- Usage Line Chart -->
                    <div class="chart-container usage-chart">
                        <div class="chart-header">
                            <h3>📉 Utilisation des Tokens</h3>
                            <div class="chart-legend">
                                <span class="legend-item">
                                    <span class="legend-dot input"></span>
                                    Input
                                </span>
                                <span class="legend-item">
                                    <span class="legend-dot output"></span>
                                    Output
                                </span>
                                <span class="legend-item">
                                    <span class="legend-dot total"></span>
                                    Total
                                </span>
                            </div>
                        </div>
                        <div class="chart-canvas-wrapper">
                            <canvas id="usage-chart"></canvas>
                        </div>
                    </div>

                    <!-- Cost Trends Chart -->
                    <div class="chart-container cost-chart">
                        <div class="chart-header">
                            <h3>💰 Tendances des Coûts</h3>
                            <div class="cost-summary">
                                <span class="cost-total">Total (période): <strong>$0.00</strong></span>
                                <span class="cost-avg">Moyenne/jour: <strong>$0.00</strong></span>
                            </div>
                        </div>
                        <div class="chart-canvas-wrapper">
                            <canvas id="cost-chart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.attachEventListeners();
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        const periodSelector = this.container.querySelector('.period-selector');
        const refreshBtn = this.container.querySelector('.btn-refresh');
        const distributionFilter = this.container.querySelector('.chart-filter');

        if (periodSelector) {
            periodSelector.addEventListener('change', (e) => {
                this.changePeriod(e.target.value);
            });
        }

        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadChartData();
            });
        }

        if (distributionFilter) {
            distributionFilter.addEventListener('change', (e) => {
                this.updateDistributionChart(e.target.value);
            });
        }
    }

    /**
     * Load chart data from API
     */
    async loadChartData() {
        try {
            const periodSelector = this.container.querySelector('.period-selector');
            if (!periodSelector) {
                console.error('Period selector not found in container');
                return;
            }
            const period = periodSelector.value;

            console.log('📥 Fetching data for period:', period);
            const [timeline, distribution, tokens, costs] = await Promise.all([
                this.fetchTimelineData(period),
                this.fetchDistributionData(period),
                this.fetchTokensData(period),
                this.fetchCostsData(period)
            ]);

            this.chartData = { timeline, distribution, tokens, costs };
            console.log('📦 Chart data loaded:', this.chartData);
            this.renderCharts();
        } catch (error) {
            console.error('Error loading chart data:', error);
        }
    }

    /**
     * Fetch timeline data
     */
    async fetchTimelineData(period) {
        // Mock data - replace with actual API call
        const days = parseInt(period);
        const data = [];
        const now = Date.now();

        for (let i = days; i >= 0; i--) {
            const date = new Date(now - i * 24 * 60 * 60 * 1000);
            data.push({
                date: date.toISOString().split('T')[0],
                messages: Math.floor(Math.random() * 50) + 10,
                threads: Math.floor(Math.random() * 5) + 1
            });
        }

        return data;
    }

    /**
     * Fetch distribution data
     */
    async fetchDistributionData(period) {
        // Mock data - replace with actual API call
        return {
            messages: {
                'Orchestrateur': 450,
                'Chercheur': 320,
                'Développeur': 280,
                'Reviewer': 150,
                'Testeur': 100
            },
            threads: {
                'Orchestrateur': 45,
                'Chercheur': 28,
                'Développeur': 22,
                'Reviewer': 15,
                'Testeur': 8
            },
            tokens: {
                'Orchestrateur': 850000,
                'Chercheur': 620000,
                'Développeur': 580000,
                'Reviewer': 320000,
                'Testeur': 180000
            }
        };
    }

    /**
     * Fetch tokens data
     */
    async fetchTokensData(period) {
        // Mock data - replace with actual API call
        const days = parseInt(period);
        const data = [];
        const now = Date.now();

        for (let i = days; i >= 0; i--) {
            const date = new Date(now - i * 24 * 60 * 60 * 1000);
            const total = Math.floor(Math.random() * 100000) + 50000;
            const input = Math.floor(total * 0.4);
            const output = total - input;

            data.push({
                date: date.toISOString().split('T')[0],
                input,
                output,
                total
            });
        }

        return data;
    }

    /**
     * Fetch costs data
     */
    async fetchCostsData(period) {
        // Mock data - replace with actual API call
        const days = parseInt(period);
        const data = [];
        const now = Date.now();

        for (let i = days; i >= 0; i--) {
            const date = new Date(now - i * 24 * 60 * 60 * 1000);
            data.push({
                date: date.toISOString().split('T')[0],
                cost: (Math.random() * 10 + 2).toFixed(2)
            });
        }

        return data;
    }

    /**
     * Render all charts
     */
    renderCharts() {
        this.renderTimelineChart();
        this.renderDistributionChart();
        this.renderTokensChart();
        this.renderCostsChart();
    }

    /**
     * Render timeline chart (Bar/Line combination)
     */
    renderTimelineChart() {
        const canvas = document.getElementById('timeline-chart');
        if (!canvas) {
            console.error('❌ Timeline chart canvas not found');
            return;
        }

        console.log('🎨 Rendering timeline chart...');
        // Wait for next frame to ensure canvas has proper dimensions
        requestAnimationFrame(() => {
            const ctx = canvas.getContext('2d');
            const data = this.chartData.timeline || [];
            console.log('📊 Timeline data:', data.length, 'items');

            // Simple canvas-based chart implementation
            this.drawTimelineChart(ctx, canvas, data);
        });
    }

    /**
     * Render distribution pie chart
     */
    renderDistributionChart() {
        const canvas = document.getElementById('distribution-chart');
        if (!canvas) return;

        requestAnimationFrame(() => {
            const ctx = canvas.getContext('2d');
            const data = this.chartData.distribution?.messages || {};

            this.drawPieChart(ctx, canvas, data);
            this.updateDistributionStats(data);
        });
    }

    /**
     * Render tokens usage chart
     */
    renderTokensChart() {
        const canvas = document.getElementById('usage-chart');
        if (!canvas) return;

        requestAnimationFrame(() => {
            const ctx = canvas.getContext('2d');
            const data = this.chartData.tokens || [];

            this.drawLineChart(ctx, canvas, data, ['input', 'output', 'total']);
        });
    }

    /**
     * Render costs trend chart
     */
    renderCostsChart() {
        const canvas = document.getElementById('cost-chart');
        if (!canvas) return;

        requestAnimationFrame(() => {
            const ctx = canvas.getContext('2d');
            const data = this.chartData.costs || [];

            this.drawAreaChart(ctx, canvas, data);
            this.updateCostSummary(data);
        });
    }

    /**
     * Draw timeline chart on canvas
     */
    drawTimelineChart(ctx, canvas, data) {
        // Get parent container dimensions
        const container = canvas.parentElement;
        const containerWidth = container.offsetWidth || 800;
        const containerHeight = container.offsetHeight || 300;

        console.log('📐 Canvas dimensions:', {
            offsetWidth: canvas.offsetWidth,
            offsetHeight: canvas.offsetHeight,
            containerWidth,
            containerHeight
        });

        const width = canvas.width = containerWidth * 2; // Retina
        const height = canvas.height = containerHeight * 2;
        ctx.scale(2, 2);

        const padding = 40;
        const chartWidth = width / 2 - padding * 2;
        const chartHeight = height / 2 - padding * 2;

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        if (!data.length) {
            // Display "no data" message
            ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
            ctx.font = '14px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Aucune donnée disponible', width / 4, height / 4);
            return;
        }

        // Find max values
        const maxMessages = Math.max(...data.map(d => d.messages));
        const maxThreads = Math.max(...data.map(d => d.threads));
        const max = Math.max(maxMessages, maxThreads);

        // Draw bars
        const barWidth = chartWidth / data.length * 0.8;
        const barGap = chartWidth / data.length * 0.2;

        console.log('📊 Drawing bars:', {
            barWidth,
            barGap,
            chartWidth,
            chartHeight,
            dataPoints: data.length,
            maxValue: max
        });

        data.forEach((item, i) => {
            const x = padding + i * (barWidth + barGap);
            const messagesHeight = (item.messages / max) * chartHeight;
            const threadsHeight = (item.threads / max) * chartHeight;

            // Messages bars
            ctx.fillStyle = '#4a90e2';
            ctx.fillRect(x, padding + chartHeight - messagesHeight, barWidth / 2, messagesHeight);

            // Threads bars
            ctx.fillStyle = '#9b59b6';
            ctx.fillRect(x + barWidth / 2, padding + chartHeight - threadsHeight, barWidth / 2, threadsHeight);
        });

        // Draw axes
        ctx.strokeStyle = '#e0e0e0';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padding, padding + chartHeight);
        ctx.lineTo(padding + chartWidth, padding + chartHeight);
        ctx.stroke();

        console.log('✅ Timeline chart drawn successfully');
    }

    /**
     * Draw pie chart on canvas
     */
    drawPieChart(ctx, canvas, data) {
        const container = canvas.parentElement;
        const containerWidth = container.offsetWidth || 400;
        const containerHeight = container.offsetHeight || 280;

        const width = canvas.width = containerWidth * 2;
        const height = canvas.height = containerHeight * 2;
        ctx.scale(2, 2);

        ctx.clearRect(0, 0, width, height);

        const centerX = width / 4;
        const centerY = height / 4;
        const radius = Math.min(width, height) / 5;

        const total = Object.values(data).reduce((sum, val) => sum + val, 0);
        const colors = ['#4a90e2', '#9b59b6', '#e74c3c', '#27ae60', '#f39c12'];

        let currentAngle = -Math.PI / 2;

        Object.entries(data).forEach(([label, value], i) => {
            const sliceAngle = (value / total) * 2 * Math.PI;

            ctx.fillStyle = colors[i % colors.length];
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
            ctx.closePath();
            ctx.fill();

            currentAngle += sliceAngle;
        });
    }

    /**
     * Draw line chart on canvas
     */
    drawLineChart(ctx, canvas, data, keys) {
        const container = canvas.parentElement;
        const containerWidth = container.offsetWidth || 800;
        const containerHeight = container.offsetHeight || 300;

        const width = canvas.width = containerWidth * 2;
        const height = canvas.height = containerHeight * 2;
        ctx.scale(2, 2);

        const padding = 40;
        const chartWidth = width / 2 - padding * 2;
        const chartHeight = height / 2 - padding * 2;

        ctx.clearRect(0, 0, width, height);

        if (!data.length) return;

        const max = Math.max(...data.flatMap(d => keys.map(k => d[k] || 0)));
        const colors = { input: '#4a90e2', output: '#e74c3c', total: '#27ae60' };

        keys.forEach(key => {
            ctx.strokeStyle = colors[key] || '#999';
            ctx.lineWidth = 2;
            ctx.beginPath();

            data.forEach((item, i) => {
                const x = padding + (i / (data.length - 1)) * chartWidth;
                const y = padding + chartHeight - ((item[key] || 0) / max) * chartHeight;

                if (i === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });

            ctx.stroke();
        });
    }

    /**
     * Draw area chart on canvas
     */
    drawAreaChart(ctx, canvas, data) {
        const container = canvas.parentElement;
        const containerWidth = container.offsetWidth || 800;
        const containerHeight = container.offsetHeight || 280;

        const width = canvas.width = containerWidth * 2;
        const height = canvas.height = containerHeight * 2;
        ctx.scale(2, 2);

        const padding = 40;
        const chartWidth = width / 2 - padding * 2;
        const chartHeight = height / 2 - padding * 2;

        ctx.clearRect(0, 0, width, height);

        if (!data.length) return;

        const max = Math.max(...data.map(d => parseFloat(d.cost)));

        // Draw area
        ctx.fillStyle = 'rgba(39, 174, 96, 0.2)';
        ctx.beginPath();

        data.forEach((item, i) => {
            const x = padding + (i / (data.length - 1)) * chartWidth;
            const y = padding + chartHeight - (parseFloat(item.cost) / max) * chartHeight;

            if (i === 0) {
                ctx.moveTo(x, padding + chartHeight);
                ctx.lineTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });

        ctx.lineTo(padding + chartWidth, padding + chartHeight);
        ctx.closePath();
        ctx.fill();

        // Draw line
        ctx.strokeStyle = '#27ae60';
        ctx.lineWidth = 2;
        ctx.beginPath();

        data.forEach((item, i) => {
            const x = padding + (i / (data.length - 1)) * chartWidth;
            const y = padding + chartHeight - (parseFloat(item.cost) / max) * chartHeight;

            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });

        ctx.stroke();
    }

    /**
     * Update distribution stats
     */
    updateDistributionStats(data) {
        const statsContainer = document.getElementById('distribution-stats');
        if (!statsContainer) return;

        const total = Object.values(data).reduce((sum, val) => sum + val, 0);
        const colors = ['#4a90e2', '#9b59b6', '#e74c3c', '#27ae60', '#f39c12'];

        const html = Object.entries(data).map(([label, value], i) => {
            const percentage = ((value / total) * 100).toFixed(1);
            return `
                <div class="stat-row">
                    <span class="stat-color" style="background: ${colors[i % colors.length]}"></span>
                    <span class="stat-label">${label}</span>
                    <span class="stat-value">${value.toLocaleString()}</span>
                    <span class="stat-percent">${percentage}%</span>
                </div>
            `;
        }).join('');

        statsContainer.innerHTML = html;
    }

    /**
     * Update cost summary
     */
    updateCostSummary(data) {
        if (!data.length) return;

        const total = data.reduce((sum, item) => sum + parseFloat(item.cost), 0);
        const avg = total / data.length;

        const totalEl = this.container.querySelector('.cost-total strong');
        const avgEl = this.container.querySelector('.cost-avg strong');

        if (totalEl) totalEl.textContent = `$${total.toFixed(2)}`;
        if (avgEl) avgEl.textContent = `$${avg.toFixed(2)}`;
    }

    /**
     * Update distribution chart based on filter
     */
    updateDistributionChart(type) {
        const data = this.chartData.distribution?.[type] || {};
        const canvas = document.getElementById('distribution-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        this.drawPieChart(ctx, canvas, data);
        this.updateDistributionStats(data);
    }

    /**
     * Change time period
     */
    async changePeriod(period) {
        await this.loadChartData();
    }

    /**
     * Cleanup
     */
    destroy() {
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Export singleton instance
export const cockpitCharts = new CockpitCharts();
