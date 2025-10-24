/**
 * Cockpit Charts Module
 * Interactive data visualizations (Timeline, Pie, Line charts)
 */

import { api } from '../../shared/api-client.js';
import { getIcon } from './cockpit-icons.js';

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
                    <h2>${getIcon('barChart')} Graphiques Interactifs</h2>
                    <div class="charts-controls">
                        <select class="period-selector">
                            <option value="7d">7 derniers jours</option>
                            <option value="30d" selected>30 derniers jours</option>
                            <option value="90d">90 derniers jours</option>
                            <option value="1y">1 an</option>
                        </select>
                        <button class="btn-refresh" title="Actualiser">${getIcon('refresh')}</button>
                    </div>
                </div>

                <div class="charts-grid">
                    <!-- Timeline Chart -->
                    <div class="chart-container timeline-chart">
                        <div class="chart-header">
                            <h3>${getIcon('activity')} Timeline d'Activité</h3>
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
                            <h3>${getIcon('pieChart')} Distribution des Agents</h3>
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
                            <h3>${getIcon('lineChart')} Utilisation des Tokens</h3>
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
                            <h3>${getIcon('dollar')} Tendances des Coûts</h3>
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
        try {
            const headers = {
                'Content-Type': 'application/json'
            };

            // Add auth token if available
            const authToken = this._getAuthToken();
            if (authToken) {
                headers['Authorization'] = `Bearer ${authToken}`;
            }

            // Add session ID if available
            const sessionId = this._getSessionId();
            if (sessionId) {
                headers['X-Session-Id'] = sessionId;
            }

            // Add dev bypass header for development mode
            headers['X-Dev-Bypass'] = '1';

            const response = await fetch(`/api/dashboard/timeline/activity?period=${period}`, {
                method: 'GET',
                headers: headers
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch activity timeline: ${response.status}`);
            }

            const data = await response.json();

            // Transform API data to expected format
            return data.map(item => ({
                date: item.date,
                messages: item.message_count || 0,
                threads: item.thread_count || 0
            }));
        } catch (error) {
            console.error('Error fetching timeline data:', error);
            // Fallback to empty array if API fails
            return [];
        }
    }

    /**
     * Fetch distribution data
     */
    async fetchDistributionData(period) {
        try {
            const headers = {
                'Content-Type': 'application/json'
            };

            // Add auth token if available
            const authToken = this._getAuthToken();
            if (authToken) {
                headers['Authorization'] = `Bearer ${authToken}`;
            }

            // Add session ID if available
            const sessionId = this._getSessionId();
            if (sessionId) {
                headers['X-Session-Id'] = sessionId;
            }

            // Add dev bypass header for development mode
            headers['X-Dev-Bypass'] = '1';

            // Fetch all distributions in parallel
            const [costsResp, threadsResp, messagesResp, tokensResp] = await Promise.all([
                fetch('/api/dashboard/costs/by-agent', { method: 'GET', headers }),
                fetch(`/api/dashboard/distribution/threads?period=${period}`, { method: 'GET', headers }),
                fetch(`/api/dashboard/distribution/messages?period=${period}`, { method: 'GET', headers }),
                fetch(`/api/dashboard/distribution/tokens?period=${period}`, { method: 'GET', headers })
            ]);

            // Parse responses (handle failures gracefully)
            const [agentCosts, threadsData, messagesData, tokensData] = await Promise.all([
                costsResp.ok ? costsResp.json() : [],
                threadsResp.ok ? threadsResp.json() : {},
                messagesResp.ok ? messagesResp.json() : {},
                tokensResp.ok ? tokensResp.json() : {}
            ]);

            const result = {
                messages: messagesData,
                threads: threadsData,
                tokens: tokensData,
                costs: {}
            };

            // Aggregate costs by agent (sum across different models)
            agentCosts.forEach(item => {
                const agent = item.agent;
                result.costs[agent] = (result.costs[agent] || 0) + item.total_cost;
            });

            return result;
        } catch (error) {
            console.error('Error fetching distribution data:', error);
            // Fallback to empty data (no mock data)
            return {
                messages: {},
                threads: {},
                tokens: {},
                costs: {}
            };
        }
    }

    /**
     * Get auth token from storage
     */
    _getAuthToken() {
        try {
            return localStorage.getItem('emergence.id_token') ||
                   localStorage.getItem('id_token') ||
                   sessionStorage.getItem('emergence.id_token') ||
                   sessionStorage.getItem('id_token');
        } catch (e) {
            return null;
        }
    }

    /**
     * Get session ID from storage
     */
    _getSessionId() {
        try {
            const state = JSON.parse(localStorage.getItem('emergenceState-V14') || '{}');
            return state.session?.id || state.websocket?.sessionId;
        } catch (e) {
            return null;
        }
    }

    /**
     * Fetch tokens data
     */
    async fetchTokensData(period) {
        try {
            const headers = {
                'Content-Type': 'application/json'
            };

            // Add auth token if available
            const authToken = this._getAuthToken();
            if (authToken) {
                headers['Authorization'] = `Bearer ${authToken}`;
            }

            // Add session ID if available
            const sessionId = this._getSessionId();
            if (sessionId) {
                headers['X-Session-Id'] = sessionId;
            }

            // Add dev bypass header for development mode
            headers['X-Dev-Bypass'] = '1';

            const response = await fetch(`/api/dashboard/timeline/tokens?period=${period}`, {
                method: 'GET',
                headers: headers
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch tokens timeline: ${response.status}`);
            }

            const data = await response.json();

            // Transform API data to expected format
            return data.map(item => ({
                date: item.date,
                input: item.input_tokens || 0,
                output: item.output_tokens || 0,
                total: (item.input_tokens || 0) + (item.output_tokens || 0)
            }));
        } catch (error) {
            console.error('Error fetching tokens data:', error);
            // Fallback to empty array if API fails
            return [];
        }
    }

    /**
     * Fetch costs data
     */
    async fetchCostsData(period) {
        try {
            const headers = {
                'Content-Type': 'application/json'
            };

            // Add auth token if available
            const authToken = this._getAuthToken();
            if (authToken) {
                headers['Authorization'] = `Bearer ${authToken}`;
            }

            // Add session ID if available
            const sessionId = this._getSessionId();
            if (sessionId) {
                headers['X-Session-Id'] = sessionId;
            }

            // Add dev bypass header for development mode
            headers['X-Dev-Bypass'] = '1';

            const response = await fetch(`/api/dashboard/timeline/costs?period=${period}`, {
                method: 'GET',
                headers: headers
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch costs timeline: ${response.status}`);
            }

            const data = await response.json();

            // Transform API data to expected format
            return data.map(item => ({
                date: item.date,
                cost: item.total_cost || 0
            }));
        } catch (error) {
            console.error('Error fetching costs data:', error);
            // Fallback to empty array if API fails
            return [];
        }
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

        const padding = 50;
        const bottomPadding = 60; // More space for date labels
        const chartWidth = width / 2 - padding * 2;
        const chartHeight = height / 2 - padding - bottomPadding;

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
        const maxMessages = Math.max(...data.map(d => d.messages || 0));
        const maxThreads = Math.max(...data.map(d => d.threads || 0));
        const max = Math.max(maxMessages, maxThreads);

        // Si toutes les données sont à 0, afficher un message
        if (max === 0) {
            ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
            ctx.font = '14px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Aucune activité pour cette période', width / 4, height / 4);
            return;
        }

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
            const messagesHeight = ((item.messages || 0) / max) * chartHeight;
            const threadsHeight = ((item.threads || 0) / max) * chartHeight;

            // Messages bars
            ctx.fillStyle = '#4a90e2';
            ctx.fillRect(x, padding + chartHeight - messagesHeight, barWidth / 2, messagesHeight);

            // Threads bars
            ctx.fillStyle = '#9b59b6';
            ctx.fillRect(x + barWidth / 2, padding + chartHeight - threadsHeight, barWidth / 2, threadsHeight);

            // Draw date labels (show every few days for readability)
            if (data.length <= 10 || i % Math.ceil(data.length / 10) === 0) {
                ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
                ctx.font = '10px sans-serif';
                ctx.textAlign = 'center';
                ctx.save();
                ctx.translate(x + barWidth / 2, padding + chartHeight + 15);
                ctx.rotate(-Math.PI / 4);
                const dateLabel = new Date(item.date).toLocaleDateString('fr-FR', { month: 'short', day: 'numeric' });
                ctx.fillText(dateLabel, 0, 0);
                ctx.restore();
            }
        });

        // Draw axes
        ctx.strokeStyle = '#e0e0e0';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padding, padding + chartHeight);
        ctx.lineTo(padding + chartWidth, padding + chartHeight);
        ctx.stroke();

        // Draw Y-axis labels
        ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
        ctx.font = '11px sans-serif';
        ctx.textAlign = 'right';
        for (let i = 0; i <= 4; i++) {
            const value = Math.round(max * i / 4);
            const y = padding + chartHeight - (chartHeight * i / 4);
            ctx.fillText(value.toString(), padding - 10, y + 4);
        }

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

        const padding = 50;
        const bottomPadding = 60;
        const chartWidth = width / 2 - padding * 2;
        const chartHeight = height / 2 - padding - bottomPadding;

        ctx.clearRect(0, 0, width, height);

        if (!data.length) {
            ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
            ctx.font = '14px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Aucune donnée disponible', width / 4, height / 4);
            return;
        }

        const max = Math.max(...data.flatMap(d => keys.map(k => d[k] || 0)));
        const colors = { input: '#4a90e2', output: '#e74c3c', total: '#27ae60' };

        // Draw grid lines
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
        ctx.lineWidth = 1;
        for (let i = 0; i <= 4; i++) {
            const y = padding + (chartHeight * i / 4);
            ctx.beginPath();
            ctx.moveTo(padding, y);
            ctx.lineTo(padding + chartWidth, y);
            ctx.stroke();
        }

        // Draw lines
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

        // Draw Y-axis labels with K/M formatting
        ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
        ctx.font = '11px sans-serif';
        ctx.textAlign = 'right';
        for (let i = 0; i <= 4; i++) {
            const value = Math.round(max * i / 4);
            const y = padding + chartHeight - (chartHeight * i / 4);
            const label = this.formatTokenValue(value);
            ctx.fillText(label, padding - 10, y + 4);
        }

        // Draw axes
        ctx.strokeStyle = '#e0e0e0';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padding, padding + chartHeight);
        ctx.lineTo(padding + chartWidth, padding + chartHeight);
        ctx.stroke();
    }

    /**
     * Format token values with K/M suffixes
     */
    formatTokenValue(value) {
        if (value >= 1000000) {
            return (value / 1000000).toFixed(1) + 'M';
        }
        if (value >= 1000) {
            return (value / 1000).toFixed(1) + 'K';
        }
        return value.toString();
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

        const padding = 50;
        const bottomPadding = 60;
        const chartWidth = width / 2 - padding * 2;
        const chartHeight = height / 2 - padding - bottomPadding;

        ctx.clearRect(0, 0, width, height);

        if (!data.length) {
            ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
            ctx.font = '14px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Aucune donnée disponible', width / 4, height / 4);
            return;
        }

        const max = Math.max(...data.map(d => parseFloat(d.cost)));

        // Draw grid lines
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
        ctx.lineWidth = 1;
        for (let i = 0; i <= 4; i++) {
            const y = padding + (chartHeight * i / 4);
            ctx.beginPath();
            ctx.moveTo(padding, y);
            ctx.lineTo(padding + chartWidth, y);
            ctx.stroke();
        }

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

        // Draw Y-axis labels with $ formatting
        ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
        ctx.font = '11px sans-serif';
        ctx.textAlign = 'right';
        for (let i = 0; i <= 4; i++) {
            const value = (max * i / 4).toFixed(2);
            const y = padding + chartHeight - (chartHeight * i / 4);
            ctx.fillText('$' + value, padding - 10, y + 4);
        }

        // Draw X-axis date labels
        ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'center';
        data.forEach((item, i) => {
            if (data.length <= 10 || i % Math.ceil(data.length / 10) === 0) {
                const x = padding + (i / (data.length - 1)) * chartWidth;
                ctx.save();
                ctx.translate(x, padding + chartHeight + 15);
                ctx.rotate(-Math.PI / 4);
                const dateLabel = new Date(item.date).toLocaleDateString('fr-FR', { month: 'short', day: 'numeric' });
                ctx.fillText(dateLabel, 0, 0);
                ctx.restore();
            }
        });

        // Draw axes
        ctx.strokeStyle = '#e0e0e0';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padding, padding + chartHeight);
        ctx.lineTo(padding + chartWidth, padding + chartHeight);
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
