
interface WeatherData {
  temperature: string;
  humidity: string;
  windSpeed: string;
  precipitation: string;
  location: string;
  description?: string;
  pressure?: string;
  visibility?: string;
  cloudCover?: string;
  feelsLike?: string;
  weatherIcon?: string;
  isRealData?: boolean;
}

class WeatherService {
  private apiKey = import.meta.env.VITE_OPENWEATHER_API_KEY;
  private baseUrl = 'https://api.openweathermap.org/data/2.5/weather';
  private lastRealDataTime: Date | null = null;
  private lastSuccessfulLocation: string | null = null;

  async getRealTimeWeatherData(location: 'thies' | 'taiba-ndiaye' | 'hann-maristes' | 'dakar' | 'bargny'): Promise<WeatherData | null> {
    console.log(`🔍 DEBUG: Début récupération météo pour ${location}`);
    console.log(`🔍 DEBUG: API Key disponible: ${!!this.apiKey}`);
    
    if (!this.apiKey) {
      console.warn('⚠️ DEBUG: Clé API OpenWeather manquante - utilisation données de secours uniquement');
      const fallbackData = this.getFallbackData(location);
      fallbackData.isRealData = false;
      return fallbackData;
    }

    const cityMapping = {
      'thies': 'Thiès,SN',
      'taiba-ndiaye': 'Taiba Ndiaye,SN', 
      'hann-maristes': 'Hann,SN',
      'dakar': 'Dakar,SN',
      'bargny': 'Bargny,SN'
    };

    const cityQuery = cityMapping[location] || 'Thiès,SN';
    console.log(`🔍 DEBUG: Requête pour ville: ${cityQuery}`);
    
    try {
      const url = `${this.baseUrl}?q=${encodeURIComponent(cityQuery)}&appid=${this.apiKey}&units=metric&lang=fr`;
      console.log(`🌍 DEBUG: URL complète: ${url.replace(this.apiKey, 'HIDDEN_API_KEY')}`);
      
      const response = await fetch(url, { 
        headers: {
          'Accept': 'application/json'
        }
      });

      console.log(`🔍 DEBUG: Statut réponse: ${response.status}`);
      
      if (!response.ok) {
        console.error(`❌ DEBUG: Erreur API: ${response.status} ${response.statusText}`);
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      console.log(`🔍 DEBUG: Données API reçues:`, data);
      
      // Valider que les données sont complètes
      if (!data.main || !data.weather || !data.wind) {
        console.error('❌ DEBUG: Données API incomplètes:', { main: !!data.main, weather: !!data.weather, wind: !!data.wind });
        throw new Error('Données API incomplètes');
      }

      this.lastRealDataTime = new Date();
      this.lastSuccessfulLocation = location;
      const weatherData = this.formatOpenWeatherData(data);
      
      console.log(`✅ DEBUG: Données météo temps réel formatées avec succès`);
      console.log(`✅ DEBUG: Description finale: ${weatherData.description}`);
      return weatherData;

    } catch (error) {
      console.error(`❌ DEBUG: Échec récupération données temps réel pour ${location}:`, error);
      
      // Utiliser les données de secours uniquement en cas d'échec
      console.log(`🔄 DEBUG: Basculement vers données de secours pour ${location}`);
      const fallbackData = this.getFallbackData(location);
      fallbackData.isRealData = false;
      console.log(`🔄 DEBUG: Données de secours créées avec description: ${fallbackData.description}`);
      return fallbackData;
    }
  }

  private formatOpenWeatherData(data: any): WeatherData {
    console.log(`🔍 DEBUG: Formatage données OpenWeather - description originale: ${data.weather[0].description}`);
    
    // Calcul précipitations (pluie + neige sur 1h)
    let precipitation = 0;
    if (data.rain?.['1h']) precipitation += data.rain['1h'];
    if (data.snow?.['1h']) precipitation += data.snow['1h'];

    // Utiliser la vraie description météo d'OpenWeather
    const realDescription = data.weather[0].description.charAt(0).toUpperCase() + data.weather[0].description.slice(1);
    
    const formattedData = {
      temperature: `${Math.round(data.main.temp)}°C`,
      humidity: `${data.main.humidity}%`,
      windSpeed: `${Math.round(data.wind.speed * 3.6)} km/h`,
      precipitation: `${precipitation.toFixed(1)} mm`,
      location: data.name,
      description: realDescription, // Description réelle d'OpenWeather
      pressure: `${data.main.pressure} hPa`,
      feelsLike: `${Math.round(data.main.feels_like)}°C`,
      visibility: data.visibility ? `${(data.visibility / 1000).toFixed(1)} km` : undefined,
      cloudCover: data.clouds ? `${data.clouds.all}%` : undefined,
      weatherIcon: this.getWeatherIcon(data.weather[0].icon),
      isRealData: true // VRAIES données OpenWeather
    };
    
    console.log(`🔍 DEBUG: Données formatées - description finale: ${formattedData.description}, isRealData: ${formattedData.isRealData}`);
    return formattedData;
  }

  private getWeatherIcon(iconCode: string): string {
    const iconMapping = {
      "01d": "sun", "01n": "moon",
      "02d": "cloud", "02n": "cloud",
      "03d": "cloud", "03n": "cloud",
      "04d": "cloud", "04n": "cloud",
      "09d": "rain", "09n": "rain",
      "10d": "rain", "10n": "rain",
      "11d": "storm", "11n": "storm",
      "13d": "snow", "13n": "snow",
      "50d": "mist", "50n": "mist"
    };
    return iconMapping[iconCode] || "sun";
  }

  private getFallbackData(location: string): WeatherData {
    console.log(`🔍 DEBUG: Génération données de secours pour ${location}`);
    
    const locationNames = {
      'thies': 'Thiès',
      'taiba-ndiaye': 'Taïba Ndiaye',
      'hann-maristes': 'Hann Maristes', 
      'dakar': 'Dakar',
      'bargny': 'Bargny'
    };

    // Données de secours réalistes pour la région
    const currentMonth = new Date().getMonth() + 1;
    const isDrySeason = [11, 12, 1, 2, 3, 4, 5].includes(currentMonth);
    
    // Variation légère pour simuler des conditions changeantes
    const tempVariation = Math.floor(Math.random() * 4) - 2;
    const humidityVariation = Math.floor(Math.random() * 10) - 5;
    
    const fallbackData = isDrySeason ? {
      temperature: `${28 + tempVariation}°C`,
      humidity: `${55 + humidityVariation}%`,
      windSpeed: `${12 + Math.floor(Math.random() * 6)} km/h`,
      precipitation: `${(Math.random() * 1.2).toFixed(1)} mm`,
      location: locationNames[location as keyof typeof locationNames] || 'Thiès',
      description: 'Données de secours - Saison sèche',
      pressure: `${1014 + Math.floor(Math.random() * 8)} hPa`,
      feelsLike: `${30 + tempVariation}°C`,
      visibility: `${10 + Math.floor(Math.random() * 5)} km`,
      cloudCover: `${Math.floor(Math.random() * 30)}%`,
      weatherIcon: 'sun',
      isRealData: false
    } : {
      temperature: `${25 + tempVariation}°C`,
      humidity: `${78 + humidityVariation}%`,
      windSpeed: `${10 + Math.floor(Math.random() * 8)} km/h`,
      precipitation: `${(8 + Math.random() * 15).toFixed(1)} mm`,
      location: locationNames[location as keyof typeof locationNames] || 'Thiès',
      description: 'Données de secours - Saison des pluies',
      pressure: `${1010 + Math.floor(Math.random() * 6)} hPa`,
      feelsLike: `${27 + tempVariation}°C`,
      visibility: `${6 + Math.floor(Math.random() * 4)} km`,
      cloudCover: `${60 + Math.floor(Math.random() * 30)}%`,
      weatherIcon: 'rain',
      isRealData: false
    };
    
    console.log(`🔍 DEBUG: Données de secours générées avec description: ${fallbackData.description}`);
    return fallbackData;
  }

  // Méthode pour données de secours (legacy)
  async getWeatherData(location: string): Promise<WeatherData> {
    return this.getFallbackData(location);
  }

  isUsingRealData(): boolean {
    if (!this.lastRealDataTime) return false;
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
    return this.lastRealDataTime > fiveMinutesAgo;
  }

  getLastSuccessfulLocation(): string | null {
    return this.lastSuccessfulLocation;
  }
}

export const weatherService = new WeatherService();
export type { WeatherData };
