// WeatherDashboard - Configuration et variables globales
class WeatherDashboard {
    constructor() {
        this.apiBaseUrl = window.location.origin;
        this.weatherChart = null;
        this.predictionChart = null;
        this.currentCity = 'paris';
        this.updateInterval = null;
        
        this.init();
    }

    // Initialisation du dashboard
    init() {
        this.setupEventListeners();
        this.updateTime();
        this.setupModal();
        this.loadDashboard(this.currentCity);
        
        // Mise à jour automatique toutes les 5 minutes
        this.updateInterval = setInterval(() => {
            this.loadDashboard(this.currentCity);
        }, 300000);
        
        // Mise à jour de l'heure chaque minute
        setInterval(() => this.updateTime(), 60000);
    }

    // Configuration des événements
    setupEventListeners() {
        const citySelect = document.getElementById('city-select');
        if (citySelect) {
            citySelect.addEventListener('change', (e) => {
                this.currentCity = e.target.value;
                this.loadDashboard(this.currentCity);
            });
        }

        const scoreInfoBtn = document.getElementById('scoreInfo');
        if (scoreInfoBtn) {
            scoreInfoBtn.addEventListener('click', () => this.openModal());
        }

        const closeModalBtn = document.getElementById('closeModal');
        if (closeModalBtn) {
            closeModalBtn.addEventListener('click', () => this.closeModal());
        }

        const modal = document.getElementById('scoreModal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) this.closeModal();
            });
        }
    }

    // Mise à jour de l'heure
    updateTime() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('fr-FR', { 
            hour: '2-digit', 
            minute: '2-digit'
        });
        const timeElement = document.getElementById('currentTime');
        if (timeElement) {
            timeElement.textContent = timeString;
        }
    }

    // Chargement principal du dashboard
    async loadDashboard(city) {
        try {
            this.showLoading();
            const response = await fetch(`${this.apiBaseUrl}/api/dashboard/${city}`);
            
            if (!response.ok) {
                throw new Error(`Erreur HTTP: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Mise à jour de toutes les sections
            this.updateKPIs(data);
            this.updateWeatherSection(data.weather);
            this.updateAirQualitySection(data.air);
            this.updateScoreSection(data.score);
            this.updateEventsSection(data.events);
            this.updatePredictionSection(data.prediction);
            this.updateCharts(data);
            
            this.hideError();
            
        } catch (error) {
            console.error('Erreur lors du chargement:', error);
            this.showError('Erreur de connexion à l\'API');
            this.loadFallbackData(city);
        }
    }

    // Mise à jour des KPIs
    updateKPIs(data) {
        this.updateElement('kpiScore', data.score?.score || '--');
        this.updateElement('kpiAir', data.air?.aqi || '--');
        this.updateElement('kpiTemp', data.weather?.current?.temperature ? `${data.weather.current.temperature}°C` : '--');
        this.updateElement('kpiEvents', data.events?.count || '--');
    }

    // Mise à jour de la section météo
    updateWeatherSection(weather) {
        if (!weather?.current) return;

        const current = weather.current;
        this.updateElement('current-temp', `${current.temperature}°C`);
        this.updateElement('feels-like', `${current.feels_like}°C`);
        this.updateElement('humidity', `${current.humidity}%`);
        this.updateElement('wind', `${current.wind_speed} km/h`);
        this.updateElement('pressure', `${current.pressure} hPa`);
        this.updateElement('visibility', `${current.visibility} km`);
        this.updateElement('weather-desc-text', current.description);

        // Icône météo OpenWeatherMap
        const iconImg = document.getElementById('weather-icon-img');
        if (iconImg && current.icon) {
            iconImg.src = `https://openweathermap.org/img/wn/${current.icon}@4x.png`;
            iconImg.alt = current.description;
        }

        // Mise à jour du timestamp
        const updateTime = document.getElementById('weather-update-time');
        if (updateTime) {
            const now = new Date();
            updateTime.textContent = `Mis à jour à ${now.toLocaleTimeString('fr-FR')}`;
        }
    }

    // Mise à jour de la section qualité de l'air
    updateAirQualitySection(air) {
        if (!air) return;

        this.updateElement('aqiValue', air.aqi);
        this.updateElement('aqiStatus', air.label || 'Chargement...');
        this.updateElement('pm25', `${air.pm25} µg/m³`);
        this.updateElement('no2', `${air.no2} µg/m³`);
        this.updateElement('o3', `${air.o3} µg/m³`);

        // Mise à jour du cercle de progression AQI
        const airCircle = document.getElementById('airCircle');
        if (airCircle) {
            const circumference = 502.6;
            const offset = circumference - (air.aqi / 500) * circumference;
            airCircle.style.strokeDashoffset = offset;
        }

        // Mise à jour des conseils avec couleurs
        this.updateAirAdvice(air);
    }

    // Mise à jour des conseils qualité de l'air
    updateAirAdvice(air) {
        const adviceElement = document.getElementById('air-advice');
        if (!adviceElement) return;

        const colorConfig = {
            'green': {
                bg: 'from-green-50 to-emerald-50 border-green-200',
                icon: 'fas fa-check text-green-600',
                text: 'text-green-800',
                iconBg: 'bg-green-100'
            },
            'yellow': {
                bg: 'from-yellow-50 to-amber-50 border-yellow-200',
                icon: 'fas fa-exclamation-triangle text-yellow-600',
                text: 'text-yellow-800',
                iconBg: 'bg-yellow-100'
            },
            'orange': {
                bg: 'from-orange-50 to-red-50 border-orange-200',
                icon: 'fas fa-exclamation text-orange-600',
                text: 'text-orange-800',
                iconBg: 'bg-orange-100'
            },
            'red': {
                bg: 'from-red-50 to-pink-50 border-red-200',
                icon: 'fas fa-times text-red-600',
                text: 'text-red-800',
                iconBg: 'bg-red-100'
            }
        };

        const config = colorConfig[air.color] || colorConfig['green'];
        
        adviceElement.className = `p-8 bg-gradient-to-br ${config.bg} border-2 rounded-3xl`;
        adviceElement.innerHTML = `
            <div class="flex items-start space-x-4">
                <div class="w-12 h-12 ${config.iconBg} rounded-2xl flex items-center justify-center flex-shrink-0">
                    <i class="${config.icon} text-xl"></i>
                </div>
                <div>
                    <div class="font-bold ${config.text} mb-2 text-lg">${air.label}</div>
                    <div class="${config.text}">${air.advice}</div>
                </div>
            </div>
        `;
    }

    // Mise à jour de la section score
    updateScoreSection(score) {
        if (!score) return;

        this.updateElement('urbanScore', score.score);
        this.updateElement('urbanScoreLabel', score.label);

        // Mise à jour du cercle de progression
        const progressCircle = document.getElementById('progressCircle');
        if (progressCircle) {
            const circumference = 282.7;
            const offset = circumference - (score.score / 100) * circumference;
            progressCircle.style.strokeDashoffset = offset;
        }

        // Mise à jour du statut avec couleurs
        this.updateScoreStatus(score);
    }

    // Mise à jour du statut du score
    updateScoreStatus(score) {
        const statusElement = document.getElementById('scoreStatus');
        if (!statusElement) return;

        const statusConfig = {
            'Excellent': { bg: 'bg-green-50 border-green-200', text: 'text-green-800' },
            'Bon': { bg: 'bg-blue-50 border-blue-200', text: 'text-blue-800' },
            'Moyen': { bg: 'bg-yellow-50 border-yellow-200', text: 'text-yellow-800' },
            'Mauvais': { bg: 'bg-red-50 border-red-200', text: 'text-red-800' }
        };

        const config = statusConfig[score.label] || statusConfig['Bon'];
        
        statusElement.className = `text-center p-6 ${config.bg} border-2 rounded-2xl backdrop-blur-lg`;
        statusElement.innerHTML = `
            <div class="${config.text} font-bold text-lg">${score.label}</div>
            <div class="${config.text} text-base mt-2">Score urbain: ${score.score}/100</div>
        `;
    }

    // Mise à jour de la section événements
    updateEventsSection(events) {
        const eventsList = document.getElementById('forecast-list');
        if (!eventsList) return;

        if (!events?.events || events.events.length === 0) {
            eventsList.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <i class="fas fa-calendar-times text-4xl mb-4 text-gray-300"></i>
                    <p>Aucun événement trouvé</p>
                </div>
            `;
            return;
        }

        const categoryIcons = {
            'culture': 'fas fa-theater-masks',
            'sport': 'fas fa-futbol',
            'marché': 'fas fa-shopping-basket',
            'concert': 'fas fa-music',
            'exposition': 'fas fa-palette'
        };

        const eventsHTML = events.events.slice(0, 4).map(event => {
            const date = new Date(event.date);
            const formattedDate = date.toLocaleDateString('fr-FR', { 
                day: 'numeric', 
                month: 'short',
                hour: '2-digit',
                minute: '2-digit'
            });

            return `
                <div class="event-card p-6 rounded-2xl">
                    <div class="flex items-start space-x-4">
                        <div class="w-12 h-12 bg-indigo-100 rounded-2xl flex items-center justify-center flex-shrink-0">
                            <i class="${categoryIcons[event.category] || 'fas fa-calendar'} text-indigo-600"></i>
                        </div>
                        <div class="flex-1">
                            <h4 class="font-bold text-gray-800 mb-2">${event.name}</h4>
                            <div class="space-y-1 text-sm text-gray-600">
                                <div class="flex items-center">
                                    <i class="fas fa-clock mr-2 text-gray-400"></i>
                                    <span>${formattedDate}</span>
                                </div>
                                <div class="flex items-center">
                                    <i class="fas fa-map-marker-alt mr-2 text-gray-400"></i>
                                    <span>${event.location}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        eventsList.innerHTML = eventsHTML;
    }

    // Mise à jour de la section prédictions
    updatePredictionSection(prediction) {
        if (!prediction) return;

        this.updateElement('prediction', prediction.predicted_aqi_6h || '--');
        this.updateElement('confidence', `${prediction.confidence || '--'}%`);

        // Mise à jour de la tendance
        this.updatePredictionTrend(prediction);

        // Mise à jour de la grille de prédiction
        if (prediction.forecast && prediction.forecast.length >= 3) {
            const gridItems = document.querySelectorAll('#prediction-grid > div');
            [1, 3, 5].forEach((index, i) => {
                if (prediction.forecast[index] && gridItems[i]) {
                    const aqiValue = gridItems[i].querySelector('.data-point');
                    if (aqiValue) {
                        aqiValue.textContent = prediction.forecast[index].aqi;
                    }
                }
            });
        }

        // Mise à jour de la recommandation IA
        this.updateAIRecommendation(prediction);
    }

    // Mise à jour de la tendance de prédiction
    updatePredictionTrend(prediction) {
        const trendElement = document.getElementById('prediction-trend');
        if (!trendElement) return;

        const currentAqi = parseInt(document.getElementById('aqiValue')?.textContent) || 0;
        const predictedAqi = prediction.predicted_aqi_6h || 0;

        if (predictedAqi < currentAqi) {
            trendElement.innerHTML = `
                <i class="fas fa-arrow-down text-green-600 mr-2"></i>
                <span class="font-bold text-green-700">Amélioration</span>
            `;
            trendElement.className = 'flex items-center text-sm text-green-600 bg-green-50 px-4 py-2 rounded-2xl border border-green-200';
        } else if (predictedAqi > currentAqi) {
            trendElement.innerHTML = `
                <i class="fas fa-arrow-up text-red-600 mr-2"></i>
                <span class="font-bold text-red-700">Dégradation</span>
            `;
            trendElement.className = 'flex items-center text-sm text-red-600 bg-red-50 px-4 py-2 rounded-2xl border border-red-200';
        } else {
            trendElement.innerHTML = `
                <i class="fas fa-minus text-blue-600 mr-2"></i>
                <span class="font-bold text-blue-700">Stable</span>
            `;
            trendElement.className = 'flex items-center text-sm text-blue-600 bg-blue-50 px-4 py-2 rounded-2xl border border-blue-200';
        }
    }

    // Mise à jour de la recommandation IA
    updateAIRecommendation(prediction) {
        const recommendationElement = document.getElementById('ai-recommendation');
        if (!recommendationElement) return;

        const predictedAqi = prediction.predicted_aqi_6h || 0;
        let config = {
            text: "Analyse en cours des conditions urbaines...",
            bg: "from-gray-50 to-gray-100 border-gray-200",
            icon: "fas fa-lightbulb text-gray-600",
            title: "text-gray-800",
            content: "text-gray-700",
            iconBg: "bg-gray-100"
        };

        if (predictedAqi <= 50) {
            config = {
                text: "Conditions excellentes prévues. Parfait pour toutes les activités outdoor.",
                bg: "from-green-50 to-emerald-50 border-green-200",
                icon: "fas fa-check text-green-600",
                title: "text-green-800",
                content: "text-green-700",
                iconBg: "bg-green-100"
            };
        } else if (predictedAqi <= 100) {
            config = {
                text: "Qualité d'air modérée attendue. Activités outdoor recommandées avec modération.",
                bg: "from-blue-50 to-cyan-50 border-blue-200",
                icon: "fas fa-info text-blue-600",
                title: "text-blue-800",
                content: "text-blue-700",
                iconBg: "bg-blue-100"
            };
        } else {
            config = {
                text: "Dégradation de la qualité d'air prévue. Limitez les activités outdoor intensives.",
                bg: "from-orange-50 to-red-50 border-orange-200",
                icon: "fas fa-exclamation-triangle text-orange-600",
                title: "text-orange-800",
                content: "text-orange-700",
                iconBg: "bg-orange-100"
            };
        }

        recommendationElement.className = `p-8 bg-gradient-to-br ${config.bg} border-2 rounded-3xl`;
        recommendationElement.innerHTML = `
            <div class="flex items-start space-x-4">
                <div class="w-12 h-12 ${config.iconBg} rounded-2xl flex items-center justify-center flex-shrink-0">
                    <i class="${config.icon} text-xl"></i>
                </div>
                <div>
                    <div class="font-bold ${config.title} mb-2 text-lg">Recommandation IA</div>
                    <div class="${config.content}">${config.text}</div>
                </div>
            </div>
        `;
    }

    // Mise à jour des graphiques
    updateCharts(data) {
        this.updateWeatherChart(data.weather);
        this.updatePredictionChart(data.prediction);
    }

    // Graphique météo
    updateWeatherChart(weather) {
        const ctx = document.getElementById('weatherChart');
        if (!ctx) return;

        if (this.weatherChart) {
            this.weatherChart.destroy();
        }

        if (!weather?.forecast_24h) return;

        const labels = weather.forecast_24h.map(item => {
            const date = new Date(item.time);
            return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
        });

        const temperatures = weather.forecast_24h.map(item => item.temp);
        const humidity = weather.forecast_24h.map(item => item.humidity);

        this.weatherChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Température (°C)',
                    data: temperatures,
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    tension: 0.4,
                    yAxisID: 'y'
                }, {
                    label: 'Humidité (%)',
                    data: humidity,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top' }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: { display: true, text: 'Température (°C)' }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: { display: true, text: 'Humidité (%)' },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });
    }

    // Graphique prédiction
    updatePredictionChart(prediction) {
        const ctx = document.getElementById('predictionChart');
        if (!ctx) return;

        if (this.predictionChart) {
            this.predictionChart.destroy();
        }

        if (!prediction?.forecast) return;

        const labels = prediction.forecast.map(item => item.hour);
        const values = prediction.forecast.map(item => item.aqi);

        this.predictionChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'AQI Prédit',
                    data: values,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'AQI' }
                    }
                }
            }
        });
    }

    // Gestion du modal
    setupModal() {
        // Déjà configuré dans setupEventListeners
    }

    openModal() {
        const modal = document.getElementById('scoreModal');
        if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('flex');
            setTimeout(() => {
                const content = modal.querySelector('.modal-content');
                if (content) {
                    content.classList.remove('scale-95');
                    content.classList.add('scale-100');
                }
            }, 10);
            this.updateModalData();
        }
    }

    closeModal() {
        const modal = document.getElementById('scoreModal');
        if (modal) {
            const content = modal.querySelector('.modal-content');
            if (content) {
                content.classList.remove('scale-100');
                content.classList.add('scale-95');
            }
            setTimeout(() => {
                modal.classList.remove('flex');
                modal.classList.add('hidden');
            }, 300);
        }
    }

    updateModalData() {
        // Simuler les données de breakdown
        const breakdown = { weather: 85, air_quality: 72, events: 76 };
        
        this.updateElement('modal-weather-score', breakdown.weather);
        this.updateElement('modal-air-score', breakdown.air_quality);
        this.updateElement('modal-events-score', breakdown.events);
        
        // Animer les barres de progression
        setTimeout(() => {
            const weatherBar = document.getElementById('modal-weather-bar');
            const airBar = document.getElementById('modal-air-bar');
            const eventsBar = document.getElementById('modal-events-bar');
            
            if (weatherBar) weatherBar.style.width = `${breakdown.weather}%`;
            if (airBar) airBar.style.width = `${breakdown.air_quality}%`;
            if (eventsBar) eventsBar.style.width = `${breakdown.events}%`;
        }, 500);
    }

    // Données de fallback
    loadFallbackData(city) {
        const fallbackData = {
            weather: {
                current: { temperature: 22, feels_like: 25, humidity: 65, wind_speed: 12, pressure: 1013, visibility: 15, description: "Données simulées", icon: "01d" },
                forecast_24h: [
                    { time: "2026-03-20 15:00:00", temp: 23, humidity: 63 },
                    { time: "2026-03-20 18:00:00", temp: 21, humidity: 67 },
                    { time: "2026-03-20 21:00:00", temp: 19, humidity: 70 },
                    { time: "2026-03-21 00:00:00", temp: 17, humidity: 73 }
                ]
            },
            air: { aqi: 45, pm25: 12, no2: 28, o3: 85, label: "Bon", color: "green", advice: "Parfait pour les activités outdoor" },
            score: { score: 78, label: "Excellent" },
            events: { events: [{ name: 'Événement test', date: '2026-03-20T19:00:00', location: 'Centre-ville', category: 'culture' }], count: 1 },
            prediction: { predicted_aqi_6h: 42, confidence: 87, forecast: [{ hour: "+1h", aqi: 47 }, { hour: "+2h", aqi: 45 }, { hour: "+3h", aqi: 44 }] }
        };

        this.updateKPIs(fallbackData);
        this.updateWeatherSection(fallbackData.weather);
        this.updateAirQualitySection(fallbackData.air);
        this.updateScoreSection(fallbackData.score);
        this.updateEventsSection(fallbackData.events);
        this.updatePredictionSection(fallbackData.prediction);
        this.updateCharts(fallbackData);
    }

    // Utilitaires
    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }

    showLoading() {
        // Vous pouvez ajouter des indicateurs de chargement ici
    }

    showError(message) {
        const errorElement = document.getElementById('error-message');
        const errorText = document.getElementById('error-text');
        
        if (errorElement && errorText) {
            errorText.textContent = message;
            errorElement.style.display = 'block';
            errorElement.classList.add('show');
            
            setTimeout(() => {
                errorElement.classList.remove('show');
                setTimeout(() => {
                    errorElement.style.display = 'none';
                }, 300);
            }, 5000);
        }
    }

    hideError() {
        const errorElement = document.getElementById('error-message');
        if (errorElement) {
            errorElement.classList.remove('show');
            setTimeout(() => {
                errorElement.style.display = 'none';
            }, 300);
        }
    }

    // Nettoyage lors de la destruction
    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        if (this.weatherChart) {
            this.weatherChart.destroy();
        }
        if (this.predictionChart) {
            this.predictionChart.destroy();
        }
    }
}

// Initialisation automatique
document.addEventListener('DOMContentLoaded', () => {
    window.weatherDashboard = new WeatherDashboard();
});
