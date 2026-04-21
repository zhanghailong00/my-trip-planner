export interface Location {
  longitude: number;
  latitude: number;
}

export interface WeatherInfo {
  date: string;
  day_weather: string;
  night_weather: string;
  day_temp: string;
  night_temp: string;
  wind_direction: string;
  wind_power: string;
}

export interface Attraction {
  name: string;
  address: string;
  location: Location;
  visit_duration: number;
  description: string;
  category: string;
  ticket_price: number;
  rating?: number;
  image_url?: string;
  poi_id?: string;
}

export interface Meal {
  type: 'breakfast' | 'lunch' | 'dinner' | 'snack';
  name: string;
  address?: string;
  location?: Location;
  description?: string;
  estimated_cost: number;
}

export interface Hotel {
  name: string;
  address: string;
  location?: Location;
  price_range?: string;
  rating?: string;
  distance?: string;
  estimated_cost: number;
}

export interface DayPlan {
  date: string;
  day_index: number;
  day_of_week: string;
  weather?: WeatherInfo;
  attractions: Attraction[];
  meals: Meal[];
  hotel?: Hotel;
  summary: string;
}

export interface Budget {
  total_attractions: number;
  total_hotels: number;
  total_meals: number;
  total_transportation: number;
  total: number;
}

export interface TripPlan {
  city: string;
  start_date: string;
  end_date: string;
  days: number;
  days_plan: DayPlan[];
  weather_info: WeatherInfo[];
  overall_suggestions: string;
  budget: Budget;
  created_at: string;
}

export interface TripRequest {
  city: string;
  start_date: string;
  end_date: string;
  travel_days: number;
  transportation: string;
  accommodation: string;
  preferences: string[];
  free_text_input: string;
}
